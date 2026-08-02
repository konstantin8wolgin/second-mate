"""Read-only target inspection for the exact FS-01 execution basis."""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from second_mate.domain import STATE_PATH, Draft, JsonObject, ValidationError, digest_json

_DEPENDENCY_FILES = frozenset(
    {
        "Pipfile.lock",
        "package-lock.json",
        "package.json",
        "pnpm-lock.yaml",
        "poetry.lock",
        "pyproject.toml",
        "requirements-dev.txt",
        "requirements.txt",
        "uv.lock",
        "yarn.lock",
    }
)
_MANAGED_PATHS = frozenset(
    {STATE_PATH, f"{STATE_PATH}.lock", f"{STATE_PATH}.next", f"{STATE_PATH}.pending"}
)


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _git(repository: Path, *args: str) -> bytes:
    environment = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
    try:
        completed = subprocess.run(
            ["git", "--no-optional-locks", "-C", os.fspath(repository), *args],
            check=True,
            capture_output=True,
            env=environment,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValidationError(f"cannot inspect Git repository: {error}") from error
    return completed.stdout


@dataclass(frozen=True, slots=True)
class FileFact:
    path: str
    kind: str
    sha256: str
    executable: bool

    def to_json(self) -> JsonObject:
        return {
            "executable": self.executable,
            "kind": self.kind,
            "path": self.path,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class TargetRevision:
    head: str
    fingerprint: str
    files: tuple[FileFact, ...]

    def to_json(self) -> JsonObject:
        return {
            "files": [item.to_json() for item in self.files],
            "fingerprint": self.fingerprint,
            "head": self.head,
        }


@dataclass(frozen=True, slots=True)
class BaselineObservation:
    result: str
    artifact_path: str
    artifact_value: str | None
    sentinel_path: str
    sentinel_sha256: str | None

    def to_json(self) -> JsonObject:
        return {
            "artifact_path": self.artifact_path,
            "artifact_value": self.artifact_value,
            "result": self.result,
            "sentinel_path": self.sentinel_path,
            "sentinel_sha256": self.sentinel_sha256,
        }


@dataclass(frozen=True, slots=True)
class PreflightRecord:
    repository_id: str
    revision: TargetRevision
    instructions: tuple[FileFact, ...]
    dependency_state: tuple[FileFact, ...]
    affected_baseline: BaselineObservation
    existing_failures: tuple[str, ...]
    irreversible_change_required: bool
    irreversible_change_reason: str
    eligible: bool

    def to_json(self) -> JsonObject:
        return {
            "affected_baseline": self.affected_baseline.to_json(),
            "dependency_state": [item.to_json() for item in self.dependency_state],
            "eligible": self.eligible,
            "existing_failures": list(self.existing_failures),
            "instructions": [item.to_json() for item in self.instructions],
            "irreversible_change": {
                "reason": self.irreversible_change_reason,
                "required": self.irreversible_change_required,
            },
            "repository_id": self.repository_id,
            "revision": self.revision.to_json(),
            "schema_version": 1,
        }


@dataclass(frozen=True, slots=True)
class PreflightEnvelope:
    record: PreflightRecord
    digest: str

    def to_json(self) -> JsonObject:
        return {
            "preflight": self.record.to_json(),
            "preflight_digest": self.digest,
            "schema_version": 1,
        }


def _repository_root(repository: Path) -> Path:
    root = Path(os.fsdecode(_git(repository, "rev-parse", "--show-toplevel")).strip()).resolve()
    if root != repository.resolve():
        raise ValidationError("target must be the Git worktree root")
    return root


def _repository_paths(repository: Path) -> tuple[str, ...]:
    output = _git(
        repository,
        "ls-files",
        "-z",
        "--cached",
        "--others",
        "--exclude-standard",
    )
    paths = {os.fsdecode(item) for item in output.split(b"\0") if item}
    return tuple(sorted(path for path in paths if path not in _MANAGED_PATHS))


def _file_fact(repository: Path, relative_path: str) -> FileFact:
    path = repository / relative_path
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return FileFact(relative_path, "missing", _sha256(b""), False)
    executable = bool(metadata.st_mode & stat.S_IXUSR)
    if path.is_symlink():
        return FileFact(relative_path, "symlink", _sha256(os.readlink(path).encode()), executable)
    if not path.is_file():
        raise ValidationError(f"unsupported repository entry: {relative_path}")
    return FileFact(relative_path, "file", _sha256(path.read_bytes()), executable)


def inspect_revision(repository: Path) -> TargetRevision:
    """Fingerprint HEAD plus tracked and visible untracked content without Git writes."""
    root = _repository_root(repository)
    head = os.fsdecode(_git(root, "rev-parse", "HEAD")).strip()
    facts = tuple(_file_fact(root, relative_path) for relative_path in _repository_paths(root))
    fingerprint = digest_json(
        {
            "files": [item.to_json() for item in facts],
            "head": head,
        }
    )
    return TargetRevision(head=head, fingerprint=fingerprint, files=facts)


def git_private_path(repository: Path, name: str) -> Path:
    """Resolve one fixed private Git-path location for disposable run coordination."""
    if not name or "/" in name or name in {".", ".."}:
        raise ValidationError("Git-private path name is invalid")
    root = _repository_root(repository)
    raw = Path(os.fsdecode(_git(root, "rev-parse", "--git-path", name)).strip())
    return raw if raw.is_absolute() else root / raw


def inspect_instructions(repository: Path, draft: Draft) -> tuple[FileFact, ...]:
    """Fingerprint every applicable instruction file, including ignored files."""
    root = _repository_root(repository)
    candidates = {"AGENTS.md"}
    for relative_path in draft.packet.boundary.allowed_paths:
        parent = Path(relative_path).parent
        while parent != Path("."):
            candidates.add((parent / "AGENTS.md").as_posix())
            parent = parent.parent
    return tuple(_file_fact(root, path) for path in sorted(candidates) if (root / path).is_file())


def _dependency_facts(revision: TargetRevision) -> tuple[FileFact, ...]:
    return tuple(
        fact
        for fact in revision.files
        if Path(fact.path).name in _DEPENDENCY_FILES and fact.kind != "missing"
    )


def _baseline(repository: Path, draft: Draft) -> tuple[BaselineObservation, tuple[str, ...]]:
    proof = draft.packet.proof
    failures: list[str] = []
    artifact_value: str | None = None
    sentinel_sha256: str | None = None
    try:
        artifact_value = (repository / proof.artifact_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        failures.append("fixture artifact is unavailable as UTF-8 text")
    if artifact_value is not None and artifact_value != proof.before:
        failures.append("fixture artifact does not match the declared before state")
    try:
        sentinel_sha256 = _sha256((repository / proof.sentinel_path).read_bytes())
    except OSError:
        failures.append("fixture sentinel is unavailable")
    observation = BaselineObservation(
        result="pass" if not failures else "fail",
        artifact_path=proof.artifact_path,
        artifact_value=artifact_value,
        sentinel_path=proof.sentinel_path,
        sentinel_sha256=sentinel_sha256,
    )
    return observation, tuple(failures)


def preflight(draft: Draft, repository: Path) -> PreflightEnvelope:
    """Inspect and freeze the target basis without changing target or external state."""
    root = _repository_root(repository)
    revision = inspect_revision(root)
    baseline, failures = _baseline(root, draft)
    record = PreflightRecord(
        repository_id=draft.packet.repository_id,
        revision=revision,
        instructions=inspect_instructions(root, draft),
        dependency_state=_dependency_facts(revision),
        affected_baseline=baseline,
        existing_failures=failures,
        irreversible_change_required=False,
        irreversible_change_reason=(
            "FS-01 changes one recoverable fixture file and local state only"
        ),
        eligible=not failures,
    )
    record_json = record.to_json()
    return PreflightEnvelope(record=record, digest=digest_json(record_json))


def _stored_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValidationError(f"{label} must be a JSON object")
    return cast(dict[str, object], value)


def _stored_keys(value: dict[str, object], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValidationError(f"{label} fields do not match schema version 1")


def _stored_text(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{label} must be a string")
    return value


def _stored_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{label} must be a boolean")
    return value


def _stored_list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise ValidationError(f"{label} must be a list")
    return cast(list[object], value)


def _file_fact_from_json(value: object) -> FileFact:
    data = _stored_object(value, "file fact")
    _stored_keys(data, {"path", "kind", "sha256", "executable"}, "file fact")
    return FileFact(
        path=_stored_text(data["path"], "file fact path"),
        kind=_stored_text(data["kind"], "file fact kind"),
        sha256=_stored_text(data["sha256"], "file fact sha256"),
        executable=_stored_bool(data["executable"], "file fact executable"),
    )


def preflight_from_json(value: object) -> PreflightEnvelope:
    """Reconstruct and digest-check a persisted preflight envelope."""
    envelope_data = _stored_object(value, "preflight envelope")
    _stored_keys(
        envelope_data,
        {"schema_version", "preflight", "preflight_digest"},
        "preflight envelope",
    )
    if envelope_data["schema_version"] != 1:
        raise ValidationError("preflight envelope schema_version must be 1")
    record_data = _stored_object(envelope_data["preflight"], "preflight")
    _stored_keys(
        record_data,
        {
            "affected_baseline",
            "dependency_state",
            "eligible",
            "existing_failures",
            "instructions",
            "irreversible_change",
            "repository_id",
            "revision",
            "schema_version",
        },
        "preflight",
    )
    if record_data["schema_version"] != 1:
        raise ValidationError("preflight schema_version must be 1")
    revision_data = _stored_object(record_data["revision"], "preflight revision")
    _stored_keys(revision_data, {"head", "fingerprint", "files"}, "preflight revision")
    files = tuple(
        _file_fact_from_json(item)
        for item in _stored_list(revision_data["files"], "preflight revision files")
    )
    revision = TargetRevision(
        head=_stored_text(revision_data["head"], "preflight revision head"),
        fingerprint=_stored_text(revision_data["fingerprint"], "preflight revision fingerprint"),
        files=files,
    )
    expected_fingerprint = digest_json(
        {"files": [item.to_json() for item in files], "head": revision.head}
    )
    if revision.fingerprint != expected_fingerprint:
        raise ValidationError("stored target revision fingerprint is invalid")

    baseline_data = _stored_object(record_data["affected_baseline"], "affected baseline")
    _stored_keys(
        baseline_data,
        {"artifact_path", "artifact_value", "result", "sentinel_path", "sentinel_sha256"},
        "affected baseline",
    )
    artifact_value_raw = baseline_data["artifact_value"]
    sentinel_sha_raw = baseline_data["sentinel_sha256"]
    if artifact_value_raw is not None and not isinstance(artifact_value_raw, str):
        raise ValidationError("affected baseline artifact_value must be a string or null")
    if sentinel_sha_raw is not None and not isinstance(sentinel_sha_raw, str):
        raise ValidationError("affected baseline sentinel_sha256 must be a string or null")
    baseline = BaselineObservation(
        result=_stored_text(baseline_data["result"], "affected baseline result"),
        artifact_path=_stored_text(
            baseline_data["artifact_path"], "affected baseline artifact_path"
        ),
        artifact_value=artifact_value_raw,
        sentinel_path=_stored_text(
            baseline_data["sentinel_path"], "affected baseline sentinel_path"
        ),
        sentinel_sha256=sentinel_sha_raw,
    )
    irreversible_data = _stored_object(record_data["irreversible_change"], "irreversible change")
    _stored_keys(irreversible_data, {"required", "reason"}, "irreversible change")
    existing_failures = tuple(
        _stored_text(item, "existing failure")
        for item in _stored_list(record_data["existing_failures"], "existing failures")
    )
    record = PreflightRecord(
        repository_id=_stored_text(record_data["repository_id"], "preflight repository_id"),
        revision=revision,
        instructions=tuple(
            _file_fact_from_json(item)
            for item in _stored_list(record_data["instructions"], "preflight instructions")
        ),
        dependency_state=tuple(
            _file_fact_from_json(item)
            for item in _stored_list(record_data["dependency_state"], "preflight dependency_state")
        ),
        affected_baseline=baseline,
        existing_failures=existing_failures,
        irreversible_change_required=_stored_bool(
            irreversible_data["required"], "irreversible change required"
        ),
        irreversible_change_reason=_stored_text(
            irreversible_data["reason"], "irreversible change reason"
        ),
        eligible=_stored_bool(record_data["eligible"], "preflight eligible"),
    )
    stored_digest = _stored_text(envelope_data["preflight_digest"], "preflight digest")
    if digest_json(record.to_json()) != stored_digest:
        raise ValidationError("stored preflight digest is invalid")
    return PreflightEnvelope(record=record, digest=stored_digest)
