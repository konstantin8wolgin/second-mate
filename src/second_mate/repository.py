"""Read-only target inspection for the exact FS-01 execution basis."""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
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
    {
        STATE_PATH,
        f"{STATE_PATH}.lock",
        f"{STATE_PATH}.next",
        f"{STATE_PATH}.pending",
        f"{STATE_PATH}.pending.next",
    }
)
_PREFLIGHT_SCHEMA_VERSION = 2
_RECOVERABLE_FIXTURE_REASON = "FS-01 changes one recoverable fixture file and local state only"


def _is_managed_path(path: str) -> bool:
    return path in _MANAGED_PATHS or path.startswith(
        (f"{STATE_PATH}.next.", f"{STATE_PATH}.pending.next.")
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
    branch: str
    index_sha256: str
    fingerprint: str
    files: tuple[FileFact, ...]

    def to_json(self) -> JsonObject:
        return {
            "branch": self.branch,
            "files": [item.to_json() for item in self.files],
            "fingerprint": self.fingerprint,
            "head": self.head,
            "index_sha256": self.index_sha256,
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
class FixturePathInspection:
    artifact: bytes | None
    sentinel: bytes | None
    failures: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PreflightRecord:
    repository_id: str
    target_root: str
    direction_digest: str
    packet_digest: str
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
            "direction_digest": self.direction_digest,
            "eligible": self.eligible,
            "existing_failures": list(self.existing_failures),
            "instructions": [item.to_json() for item in self.instructions],
            "irreversible_change": {
                "reason": self.irreversible_change_reason,
                "required": self.irreversible_change_required,
            },
            "packet_digest": self.packet_digest,
            "repository_id": self.repository_id,
            "target_root": self.target_root,
            "revision": self.revision.to_json(),
            "schema_version": _PREFLIGHT_SCHEMA_VERSION,
        }


@dataclass(frozen=True, slots=True)
class PreflightEnvelope:
    record: PreflightRecord
    digest: str

    def to_json(self) -> JsonObject:
        return {
            "preflight": self.record.to_json(),
            "preflight_digest": self.digest,
            "schema_version": _PREFLIGHT_SCHEMA_VERSION,
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
    return tuple(sorted(path for path in paths if not _is_managed_path(path)))


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
    branch = os.fsdecode(_git(root, "rev-parse", "--abbrev-ref", "HEAD")).strip()
    index_sha256 = _sha256(
        b"stages-and-modes\0"
        + _git(root, "ls-files", "--stage", "-z")
        + b"assume-unchanged-and-skip-worktree\0"
        + _git(root, "ls-files", "--cached", "-v", "-z")
        + b"fsmonitor-valid\0"
        + _git(root, "ls-files", "--cached", "-f", "-z")
        + b"intent-to-add\0"
        + _git(
            root,
            "diff",
            "--cached",
            "--raw",
            "--no-renames",
            "--ita-invisible-in-index",
            "-z",
            "--",
        )
    )
    facts = tuple(_file_fact(root, relative_path) for relative_path in _repository_paths(root))
    fingerprint = digest_json(
        {
            "branch": branch,
            "files": [item.to_json() for item in facts],
            "head": head,
            "index_sha256": index_sha256,
        }
    )
    return TargetRevision(
        head=head,
        branch=branch,
        index_sha256=index_sha256,
        fingerprint=fingerprint,
        files=facts,
    )


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
    facts: list[FileFact] = []
    for relative_path in sorted(candidates):
        path = root / relative_path
        try:
            declared = path.lstat()
        except FileNotFoundError:
            continue
        except OSError as error:
            raise ValidationError(
                f"cannot inspect applicable instruction: {relative_path}"
            ) from error
        descriptor: int | None = None
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_nlink != 1
                or (metadata.st_dev, metadata.st_ino) != (declared.st_dev, declared.st_ino)
                or path.resolve(strict=True) != path
            ):
                raise OSError("unsafe instruction identity")
            with os.fdopen(descriptor, "rb", closefd=True) as stream:
                descriptor = None
                content = stream.read()
            declared_after = path.lstat()
            if (metadata.st_dev, metadata.st_ino) != (
                declared_after.st_dev,
                declared_after.st_ino,
            ):
                raise OSError("instruction identity changed during inspection")
        except OSError as error:
            raise ValidationError(
                f"applicable instruction must be a regular file at its declared path: "
                f"{relative_path}"
            ) from error
        finally:
            if descriptor is not None:
                os.close(descriptor)
        facts.append(
            FileFact(
                path=relative_path,
                kind="file",
                sha256=_sha256(content),
                executable=bool(metadata.st_mode & stat.S_IXUSR),
            )
        )
    return tuple(facts)


def _dependency_facts(revision: TargetRevision) -> tuple[FileFact, ...]:
    return tuple(
        fact
        for fact in revision.files
        if Path(fact.path).name in _DEPENDENCY_FILES and fact.kind != "missing"
    )


def _inspect_fixture_paths_at_root(root: Path, draft: Draft) -> FixturePathInspection:
    contents: dict[str, bytes | None] = {"artifact": None, "sentinel": None}
    failures: list[str] = []
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for label, relative_path in (
            ("artifact", draft.packet.proof.artifact_path),
            ("sentinel", draft.packet.proof.sentinel_path),
        ):
            descriptor: int | None = None
            try:
                descriptor = os.open(
                    relative_path,
                    os.O_RDONLY | os.O_NOFOLLOW,
                    dir_fd=directory,
                )
                metadata = os.fstat(descriptor)
                entry = os.stat(relative_path, dir_fd=directory, follow_symlinks=False)
                if (
                    not stat.S_ISREG(metadata.st_mode)
                    or metadata.st_nlink != 1
                    or (metadata.st_dev, metadata.st_ino) != (entry.st_dev, entry.st_ino)
                ):
                    raise OSError("unsafe fixture file identity")
                with os.fdopen(descriptor, "rb", closefd=True) as stream:
                    descriptor = None
                    content = stream.read()
                entry_after = os.stat(relative_path, dir_fd=directory, follow_symlinks=False)
                if (metadata.st_dev, metadata.st_ino) != (
                    entry_after.st_dev,
                    entry_after.st_ino,
                ):
                    raise OSError("fixture file identity changed during inspection")
                contents[label] = content
            except OSError:
                failures.append(
                    f"fixture {label} path must be one unaliased regular file at its declared path"
                )
            finally:
                if descriptor is not None:
                    os.close(descriptor)
    finally:
        os.close(directory)
    return FixturePathInspection(
        artifact=contents["artifact"],
        sentinel=contents["sentinel"],
        failures=tuple(failures),
    )


def inspect_fixture_paths(repository: Path, draft: Draft) -> FixturePathInspection:
    """Resolve proof files only when their declared paths have unaliased identities."""
    return _inspect_fixture_paths_at_root(_repository_root(repository), draft)


def _baseline(
    repository: Path,
    draft: Draft,
    revision: TargetRevision,
    recovery_intents: frozenset[str],
) -> tuple[BaselineObservation, tuple[str, ...]]:
    proof = draft.packet.proof
    failures: list[str] = []
    artifact_value: str | None = None
    sentinel_sha256: str | None = None
    state_directory = (repository / STATE_PATH).parent
    state_directory_is_safe = False
    try:
        state_metadata = state_directory.lstat()
    except FileNotFoundError:
        pass
    except OSError:
        failures.append("coordinator state directory cannot be inspected")
    else:
        if (
            not stat.S_ISDIR(state_metadata.st_mode)
            or state_directory.resolve(strict=True) != state_directory
        ):
            failures.append(
                "coordinator state directory must be a real directory inside the target"
            )
        else:
            state_directory_is_safe = True
    for relative_path in sorted(_MANAGED_PATHS):
        try:
            (repository / relative_path).lstat()
        except FileNotFoundError:
            continue
        except OSError:
            failures.append(f"reserved coordinator path cannot be inspected: {relative_path}")
        else:
            failures.append(f"reserved coordinator path already exists: {relative_path}")
    if state_directory_is_safe:
        try:
            dynamic_managed_paths: list[str] = []
            for entry in state_directory.iterdir():
                relative_path = entry.relative_to(repository).as_posix()
                if (
                    _is_managed_path(relative_path)
                    and relative_path not in _MANAGED_PATHS
                    and relative_path not in recovery_intents
                ):
                    dynamic_managed_paths.append(relative_path)
        except OSError:
            failures.append("reserved coordinator paths cannot be inspected")
        else:
            failures.extend(
                f"reserved coordinator path already exists: {relative_path}"
                for relative_path in sorted(dynamic_managed_paths)
            )
    revision_paths = {item.path: item for item in revision.files}
    for label, relative_path in (
        ("artifact", proof.artifact_path),
        ("sentinel", proof.sentinel_path),
    ):
        fact = revision_paths.get(relative_path)
        if fact is None or fact.kind != "file":
            failures.append(f"fixture {label} path must be tracked or visible untracked content")
    fixture_paths = _inspect_fixture_paths_at_root(repository, draft)
    failures.extend(fixture_paths.failures)
    if fixture_paths.artifact is not None:
        try:
            artifact_value = fixture_paths.artifact.decode("utf-8")
        except UnicodeError:
            failures.append("fixture artifact is unavailable as UTF-8 text")
    if artifact_value is not None and artifact_value != proof.before:
        failures.append("fixture artifact does not match the declared before state")
    if fixture_paths.sentinel is not None:
        sentinel_sha256 = _sha256(fixture_paths.sentinel)
    observation = BaselineObservation(
        result="pass" if not failures else "fail",
        artifact_path=proof.artifact_path,
        artifact_value=artifact_value,
        sentinel_path=proof.sentinel_path,
        sentinel_sha256=sentinel_sha256,
    )
    return observation, tuple(failures)


def preflight(
    draft: Draft,
    repository: Path,
    *,
    _recovery_intents: frozenset[str] = frozenset(),
) -> PreflightEnvelope:
    """Inspect and freeze the target basis without changing target or external state."""
    root = _repository_root(repository)
    revision = inspect_revision(root)
    baseline, failures = _baseline(root, draft, revision, _recovery_intents)
    record = PreflightRecord(
        repository_id=draft.packet.repository_id,
        target_root=os.fspath(root),
        direction_digest=draft.direction_digest,
        packet_digest=draft.packet_digest,
        revision=revision,
        instructions=inspect_instructions(root, draft),
        dependency_state=_dependency_facts(revision),
        affected_baseline=baseline,
        existing_failures=failures,
        irreversible_change_required=False,
        irreversible_change_reason=_RECOVERABLE_FIXTURE_REASON,
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
        raise ValidationError(f"{label} fields do not match the expected schema")


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


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _validate_fact_sequence(
    facts: tuple[FileFact, ...],
    *,
    label: str,
    required_kind: str | None = None,
) -> None:
    paths = tuple(item.path for item in facts)
    if paths != tuple(sorted(paths)) or len(paths) != len(set(paths)):
        raise ValidationError(f"{label} paths must be unique and sorted")
    for fact in facts:
        parsed = PurePosixPath(fact.path)
        if not fact.path or parsed.is_absolute() or ".." in parsed.parts or fact.path in {"", "."}:
            raise ValidationError(f"{label} contains an invalid repository-relative path")
        if fact.kind not in {"file", "missing", "symlink"}:
            raise ValidationError(f"{label} contains an invalid file kind")
        if required_kind is not None and fact.kind != required_kind:
            raise ValidationError(f"{label} must contain only {required_kind} facts")
        if not _valid_sha256(fact.sha256):
            raise ValidationError(f"{label} contains an invalid SHA-256 digest")


def _validate_preflight_semantics(record: PreflightRecord) -> None:
    _validate_fact_sequence(record.revision.files, label="preflight revision files")
    _validate_fact_sequence(
        record.instructions,
        label="preflight instructions",
        required_kind="file",
    )
    _validate_fact_sequence(record.dependency_state, label="preflight dependency state")
    if record.dependency_state != _dependency_facts(record.revision):
        raise ValidationError("preflight dependency state is not derived from the revision")
    if not record.repository_id.strip():
        raise ValidationError("preflight repository_id must be non-empty")
    target_root = Path(record.target_root)
    if not record.target_root or not target_root.is_absolute():
        raise ValidationError("preflight target_root must be an absolute path")
    if not record.direction_digest or not _valid_sha256(record.direction_digest):
        raise ValidationError("preflight direction digest is invalid")
    if not record.packet_digest or not _valid_sha256(record.packet_digest):
        raise ValidationError("preflight packet digest is invalid")
    revision = record.revision
    if (
        not revision.head.strip()
        or not revision.branch.strip()
        or not _valid_sha256(revision.index_sha256)
        or not _valid_sha256(revision.fingerprint)
    ):
        raise ValidationError("preflight revision identity is invalid")
    baseline = record.affected_baseline
    if baseline.result not in {"pass", "fail"}:
        raise ValidationError("preflight affected baseline result is invalid")
    if not baseline.artifact_path or not baseline.sentinel_path:
        raise ValidationError("preflight affected baseline paths must be non-empty")
    if baseline.artifact_path == baseline.sentinel_path:
        raise ValidationError("preflight affected baseline proof paths must be distinct")
    if baseline.sentinel_sha256 is not None and not _valid_sha256(baseline.sentinel_sha256):
        raise ValidationError("preflight affected baseline sentinel hash is invalid")
    if any(not failure.strip() for failure in record.existing_failures) or len(
        record.existing_failures
    ) != len(set(record.existing_failures)):
        raise ValidationError("preflight existing failures must be unique non-empty strings")
    expected_baseline_result = "pass" if not record.existing_failures else "fail"
    if baseline.result != expected_baseline_result:
        raise ValidationError(
            "preflight affected baseline result contradicts its existing failures"
        )
    if baseline.result == "pass":
        if baseline.artifact_value is None or baseline.sentinel_sha256 is None:
            raise ValidationError("preflight passing baseline omits a proof observation")
        revision_files = {item.path: item for item in revision.files}
        artifact = revision_files.get(baseline.artifact_path)
        sentinel = revision_files.get(baseline.sentinel_path)
        if (
            artifact is None
            or artifact.kind != "file"
            or artifact.sha256 != _sha256(baseline.artifact_value.encode("utf-8"))
            or sentinel is None
            or sentinel.kind != "file"
            or sentinel.sha256 != baseline.sentinel_sha256
        ):
            raise ValidationError("preflight passing baseline contradicts its frozen revision")
    if record.irreversible_change_reason != _RECOVERABLE_FIXTURE_REASON:
        raise ValidationError("preflight irreversible-change reason is invalid for FS-01")
    expected_eligible = (
        baseline.result == "pass"
        and not record.existing_failures
        and not record.irreversible_change_required
    )
    if record.eligible != expected_eligible:
        raise ValidationError("preflight eligibility contradicts its observed constraints")
    if record.irreversible_change_required:
        raise ValidationError("preflight cannot authorize an irreversible FS-01 change")


def preflight_from_json(value: object) -> PreflightEnvelope:
    """Reconstruct and digest-check a persisted preflight envelope."""
    envelope_data = _stored_object(value, "preflight envelope")
    _stored_keys(
        envelope_data,
        {"schema_version", "preflight", "preflight_digest"},
        "preflight envelope",
    )
    if (
        type(envelope_data["schema_version"]) is not int
        or envelope_data["schema_version"] != _PREFLIGHT_SCHEMA_VERSION
    ):
        raise ValidationError("preflight envelope schema_version must be the integer 2")
    record_data = _stored_object(envelope_data["preflight"], "preflight")
    _stored_keys(
        record_data,
        {
            "affected_baseline",
            "dependency_state",
            "direction_digest",
            "eligible",
            "existing_failures",
            "instructions",
            "irreversible_change",
            "packet_digest",
            "repository_id",
            "revision",
            "schema_version",
            "target_root",
        },
        "preflight",
    )
    if (
        type(record_data["schema_version"]) is not int
        or record_data["schema_version"] != _PREFLIGHT_SCHEMA_VERSION
    ):
        raise ValidationError("preflight schema_version must be the integer 2")
    revision_data = _stored_object(record_data["revision"], "preflight revision")
    _stored_keys(
        revision_data,
        {"branch", "files", "fingerprint", "head", "index_sha256"},
        "preflight revision",
    )
    files = tuple(
        _file_fact_from_json(item)
        for item in _stored_list(revision_data["files"], "preflight revision files")
    )
    revision = TargetRevision(
        head=_stored_text(revision_data["head"], "preflight revision head"),
        branch=_stored_text(revision_data["branch"], "preflight revision branch"),
        index_sha256=_stored_text(revision_data["index_sha256"], "preflight revision index_sha256"),
        fingerprint=_stored_text(revision_data["fingerprint"], "preflight revision fingerprint"),
        files=files,
    )
    expected_fingerprint = digest_json(
        {
            "branch": revision.branch,
            "files": [item.to_json() for item in files],
            "head": revision.head,
            "index_sha256": revision.index_sha256,
        }
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
        target_root=_stored_text(record_data["target_root"], "preflight target_root"),
        direction_digest=_stored_text(
            record_data["direction_digest"], "preflight direction_digest"
        ),
        packet_digest=_stored_text(record_data["packet_digest"], "preflight packet_digest"),
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
    _validate_preflight_semantics(record)
    return PreflightEnvelope(record=record, digest=stored_digest)
