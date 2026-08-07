"""Read-only preparation and durable approval of repository Direction versions."""

from __future__ import annotations

import hashlib
import os
import re
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from second_mate.domain import (
    Approval,
    Direction,
    JsonObject,
    ValidationError,
    digest_json,
    direction_from_json,
)
from second_mate.repository import (
    FileFact,
    MutationLockBusyError,
    TargetRevision,
    git_private_path,
    inspect_revision,
    mutation_lock,
    repository_path_is_ignored,
    repository_path_is_recorded,
)
from second_mate.store import (
    PosixAtomicWriter,
    StateRecoveryError,
    StrictJsonError,
    deterministic_document_bytes,
    pending_atomic_exchange,
    strict_json_loads,
)

_DIRECTION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_LEDGER_PATH = Path(".second-mate/directions.json")
_RUN_STATE_PATH = Path(".second-mate/state.json")
_RUN_PENDING_PATH = Path(".second-mate/state.json.pending")
_ALLOWED_PATHS = (".second-mate/directions.json",)
_ALLOWED_EFFECTS = ("direction_ledger_write",)
_STOP_CONDITIONS = ("revision_drift", "direction_history_drift", "open_run")


class DirectionConflictError(RuntimeError):
    """A promotion would replace, branch, or race immutable Direction history."""


@dataclass(frozen=True, slots=True)
class DirectionPredecessor:
    direction_id: str
    direction_digest: str

    def to_json(self) -> JsonObject:
        return {
            "direction_digest": self.direction_digest,
            "direction_id": self.direction_id,
        }


@dataclass(frozen=True, slots=True)
class DirectionCandidate:
    id: str
    text: str
    supersedes: DirectionPredecessor | None
    change_note: str | None

    def to_json(self) -> JsonObject:
        return {
            "change_note": self.change_note,
            "id": self.id,
            "schema_version": 1,
            "supersedes": None if self.supersedes is None else self.supersedes.to_json(),
            "text": self.text,
        }


@dataclass(frozen=True, slots=True)
class PromotionBasis:
    target_head: str
    target_fingerprint: str
    run_state_sha256: str | None

    def to_json(self) -> JsonObject:
        return {
            "run_state_sha256": self.run_state_sha256,
            "target_fingerprint": self.target_fingerprint,
            "target_head": self.target_head,
        }


@dataclass(frozen=True, slots=True)
class DirectionCandidateEnvelope:
    candidate: DirectionCandidate
    digest: str
    promotion_basis: PromotionBasis

    def to_json(self) -> JsonObject:
        return {
            "candidate": self.candidate.to_json(),
            "candidate_digest": self.digest,
            "promotion_basis": self.promotion_basis.to_json(),
            "schema_version": 1,
        }


@dataclass(frozen=True, slots=True)
class DirectionApproval:
    id: str
    direction_id: str
    candidate_digest: str
    approved_by: str
    approved_at: str
    proposal_digest: str | None = None

    def to_json(self) -> JsonObject:
        document: JsonObject = {
            "approved_at": self.approved_at,
            "approved_by": self.approved_by,
            "candidate_digest": self.candidate_digest,
            "decision": "approved",
            "direction_id": self.direction_id,
            "id": self.id,
            "schema_version": 1 if self.proposal_digest is None else 2,
        }
        if self.proposal_digest is not None:
            document["proposal_digest"] = self.proposal_digest
        return document


@dataclass(frozen=True, slots=True)
class PromotionGrant:
    id: str
    granted_by: str
    granted_at: str
    candidate_digest: str
    target_head: str
    target_fingerprint: str
    run_state_sha256: str | None
    allowed_paths: tuple[str, ...]
    allowed_effects: tuple[str, ...]
    stop_conditions: tuple[str, ...]

    def to_json(self) -> JsonObject:
        return {
            "allowed_effects": list(self.allowed_effects),
            "allowed_paths": list(self.allowed_paths),
            "candidate_digest": self.candidate_digest,
            "granted_at": self.granted_at,
            "granted_by": self.granted_by,
            "id": self.id,
            "run_state_sha256": self.run_state_sha256,
            "schema_version": 1,
            "stop_conditions": list(self.stop_conditions),
            "target_fingerprint": self.target_fingerprint,
            "target_head": self.target_head,
        }


@dataclass(frozen=True, slots=True)
class ApprovedDirectionVersion:
    direction: Direction
    direction_digest: str
    approval: DirectionApproval
    promotion_grant: PromotionGrant
    supersedes: DirectionPredecessor | None
    change_note: str | None

    def to_json(self) -> JsonObject:
        return {
            "approval": self.approval.to_json(),
            "change_note": self.change_note,
            "direction": self.direction.to_json(),
            "direction_digest": self.direction_digest,
            "promotion_grant": self.promotion_grant.to_json(),
            "supersedes": None if self.supersedes is None else self.supersedes.to_json(),
        }


@dataclass(frozen=True, slots=True)
class DirectionLedger:
    versions: tuple[ApprovedDirectionVersion, ...]

    @property
    def current(self) -> ApprovedDirectionVersion:
        if not self.versions:
            raise ValidationError("Direction ledger must contain an approved version")
        return self.versions[-1]

    def to_json(self) -> JsonObject:
        return {
            "current_direction_id": self.current.direction.id,
            "schema_version": 1,
            "versions": [version.to_json() for version in self.versions],
        }


@dataclass(frozen=True, slots=True)
class DirectionVersionLookup:
    """One validated immutable Direction version and whether it is current."""

    version: ApprovedDirectionVersion
    is_current: bool


def _direction_id(value: str) -> str:
    if not _DIRECTION_ID.fullmatch(value):
        raise ValidationError(
            "direction id must use only letters, numbers, dot, underscore, or hyphen"
        )
    return value


def _object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValidationError(f"{label} must be a JSON object")
    return cast(dict[str, object], value)


def _exact_keys(
    value: dict[str, object],
    expected: set[str],
    label: str,
    *,
    schema_version: int = 1,
) -> None:
    if set(value) != expected:
        raise ValidationError(f"{label} fields do not match schema version {schema_version}")


def _schema_one(value: object, label: str) -> None:
    if type(value) is not int or value != 1:
        raise ValidationError(f"{label} schema_version must be the integer 1")


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be a non-empty string")
    return value


def _sha256(value: object, label: str) -> str:
    digest = _text(value, label)
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValidationError(f"{label} must be a lowercase SHA-256 digest")
    return digest


def _optional_sha256(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _sha256(value, label)


def _strings(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValidationError(f"{label} must be a list of non-empty strings")
    result = tuple(cast(list[str], value))
    if len(result) != len(set(result)):
        raise ValidationError(f"{label} must contain no duplicates")
    return result


def _candidate_envelope_from_json(value: object) -> DirectionCandidateEnvelope:
    data = _object(value, "Direction candidate envelope")
    _exact_keys(
        data,
        {"schema_version", "candidate", "candidate_digest", "promotion_basis"},
        "Direction candidate envelope",
    )
    _schema_one(data["schema_version"], "Direction candidate envelope")
    candidate_data = _object(data["candidate"], "Direction candidate")
    _exact_keys(
        candidate_data,
        {"schema_version", "id", "text", "supersedes", "change_note"},
        "Direction candidate",
    )
    _schema_one(candidate_data["schema_version"], "Direction candidate")
    predecessor = _predecessor_from_json(candidate_data["supersedes"])
    change_note_raw = candidate_data["change_note"]
    if change_note_raw is not None and not isinstance(change_note_raw, str):
        raise ValidationError("Direction candidate change_note must be a string or null")
    candidate = DirectionCandidate(
        id=_direction_id(_text(candidate_data["id"], "Direction candidate id")),
        text=_text(candidate_data["text"], "Direction candidate text"),
        supersedes=predecessor,
        change_note=change_note_raw,
    )
    stored_digest = _sha256(data["candidate_digest"], "Direction candidate digest")
    if digest_json(candidate.to_json()) != stored_digest:
        raise ValidationError("Direction candidate digest does not match its exact content")
    basis_data = _object(data["promotion_basis"], "Direction promotion basis")
    _exact_keys(
        basis_data,
        {"target_head", "target_fingerprint", "run_state_sha256"},
        "Direction promotion basis",
    )
    basis = PromotionBasis(
        target_head=_text(basis_data["target_head"], "promotion basis target_head"),
        target_fingerprint=_sha256(
            basis_data["target_fingerprint"], "promotion basis target_fingerprint"
        ),
        run_state_sha256=_optional_sha256(
            basis_data["run_state_sha256"], "promotion basis run_state_sha256"
        ),
    )
    return DirectionCandidateEnvelope(
        candidate=candidate, digest=stored_digest, promotion_basis=basis
    )


def parse_direction_candidate(value: object) -> DirectionCandidateEnvelope:
    """Parse and verify one exact transport-neutral Direction candidate envelope."""
    return _candidate_envelope_from_json(value)


def _predecessor_from_json(value: object) -> DirectionPredecessor | None:
    if value is None:
        return None
    data = _object(value, "Direction predecessor")
    _exact_keys(data, {"direction_id", "direction_digest"}, "Direction predecessor")
    return DirectionPredecessor(
        direction_id=_direction_id(_text(data["direction_id"], "predecessor direction_id")),
        direction_digest=_sha256(data["direction_digest"], "predecessor direction_digest"),
    )


def _approval_from_json(value: object | None) -> DirectionApproval:
    if value is None:
        raise ValidationError("explicit Direction approval is required before promotion")
    data = _object(value, "Direction approval")
    base_keys = {
        "schema_version",
        "id",
        "decision",
        "direction_id",
        "candidate_digest",
        "approved_by",
        "approved_at",
    }
    schema_version = data.get("schema_version")
    if type(schema_version) is not int or schema_version not in {1, 2}:
        raise ValidationError("Direction approval schema_version must be the integer 1 or 2")
    expected_keys = base_keys if schema_version == 1 else {*base_keys, "proposal_digest"}
    _exact_keys(
        data,
        expected_keys,
        "Direction approval",
        schema_version=schema_version,
    )
    if data["decision"] != "approved":
        raise ValidationError("Direction approval decision must be approved")
    return DirectionApproval(
        id=_direction_id(_text(data["id"], "Direction approval id")),
        direction_id=_direction_id(_text(data["direction_id"], "Direction approval direction_id")),
        candidate_digest=_sha256(data["candidate_digest"], "Direction approval digest"),
        approved_by=_text(data["approved_by"], "Direction approval approved_by"),
        approved_at=_text(data["approved_at"], "Direction approval approved_at"),
        proposal_digest=(
            None
            if schema_version == 1
            else _sha256(data["proposal_digest"], "Direction approval proposal_digest")
        ),
    )


def _promotion_grant_from_json(value: object | None) -> PromotionGrant:
    if value is None:
        raise ValidationError("explicit Direction promotion authority is required before write")
    data = _object(value, "Direction promotion grant")
    _exact_keys(
        data,
        {
            "schema_version",
            "id",
            "granted_by",
            "granted_at",
            "candidate_digest",
            "target_head",
            "target_fingerprint",
            "run_state_sha256",
            "allowed_paths",
            "allowed_effects",
            "stop_conditions",
        },
        "Direction promotion grant",
    )
    _schema_one(data["schema_version"], "Direction promotion grant")
    grant = PromotionGrant(
        id=_direction_id(_text(data["id"], "promotion grant id")),
        granted_by=_text(data["granted_by"], "promotion grant granted_by"),
        granted_at=_text(data["granted_at"], "promotion grant granted_at"),
        candidate_digest=_sha256(data["candidate_digest"], "promotion grant candidate_digest"),
        target_head=_text(data["target_head"], "promotion grant target_head"),
        target_fingerprint=_sha256(
            data["target_fingerprint"], "promotion grant target_fingerprint"
        ),
        run_state_sha256=_optional_sha256(
            data["run_state_sha256"], "promotion grant run_state_sha256"
        ),
        allowed_paths=_strings(data["allowed_paths"], "promotion grant allowed_paths"),
        allowed_effects=_strings(data["allowed_effects"], "promotion grant allowed_effects"),
        stop_conditions=_strings(data["stop_conditions"], "promotion grant stop_conditions"),
    )
    if grant.allowed_paths != _ALLOWED_PATHS:
        raise ValidationError("promotion grant allowed_paths do not match the fixed boundary")
    if grant.allowed_effects != _ALLOWED_EFFECTS:
        raise ValidationError("promotion grant allowed_effects do not match the fixed boundary")
    if grant.stop_conditions != _STOP_CONDITIONS:
        raise ValidationError("promotion grant stop_conditions do not match the fixed boundary")
    return grant


def _version_from_json(value: object) -> ApprovedDirectionVersion:
    data = _object(value, "approved Direction version")
    _exact_keys(
        data,
        {
            "approval",
            "change_note",
            "direction",
            "direction_digest",
            "promotion_grant",
            "supersedes",
        },
        "approved Direction version",
    )
    approval = _approval_from_json(data["approval"])
    grant = _promotion_grant_from_json(data["promotion_grant"])
    direction = direction_from_json(data["direction"])
    direction_digest = _sha256(data["direction_digest"], "Direction version digest")
    if digest_json(direction.to_json()) != direction_digest:
        raise ValidationError("approved Direction version digest is invalid")
    if approval.direction_id != direction.id:
        raise ValidationError("Direction approval does not identify the approved Direction")
    if direction.approval != Approval(
        approved_by=approval.approved_by,
        approved_at=approval.approved_at,
    ):
        raise ValidationError("Direction approval disagrees with the approved Direction")
    if grant.candidate_digest != approval.candidate_digest:
        raise ValidationError("promotion authority is not bound to the approved candidate")
    predecessor = _predecessor_from_json(data["supersedes"])
    change_note_raw = data["change_note"]
    if change_note_raw is not None and not isinstance(change_note_raw, str):
        raise ValidationError("Direction version change_note must be a string or null")
    candidate = DirectionCandidate(
        id=direction.id,
        text=direction.text,
        supersedes=predecessor,
        change_note=change_note_raw,
    )
    if digest_json(candidate.to_json()) != approval.candidate_digest:
        raise ValidationError("Direction approval is not bound to the stored exact candidate")
    return ApprovedDirectionVersion(
        direction=direction,
        direction_digest=direction_digest,
        approval=approval,
        promotion_grant=grant,
        supersedes=predecessor,
        change_note=change_note_raw,
    )


def _ledger_from_json(value: object) -> DirectionLedger:
    data = _object(value, "Direction ledger")
    _exact_keys(
        data,
        {"schema_version", "current_direction_id", "versions"},
        "Direction ledger",
    )
    _schema_one(data["schema_version"], "Direction ledger")
    versions_raw = data["versions"]
    if not isinstance(versions_raw, list) or not versions_raw:
        raise ValidationError("Direction ledger must contain approved versions")
    versions = tuple(_version_from_json(item) for item in versions_raw)
    direction_ids: set[str] = set()
    approval_ids: set[str] = set()
    grant_ids: set[str] = set()
    for index, version in enumerate(versions):
        if version.direction.id in direction_ids:
            raise ValidationError("Direction ledger contains a duplicate Direction id")
        if version.approval.id in approval_ids:
            raise ValidationError("Direction ledger contains a duplicate approval id")
        if version.promotion_grant.id in grant_ids:
            raise ValidationError("Direction ledger contains a duplicate promotion grant id")
        direction_ids.add(version.direction.id)
        approval_ids.add(version.approval.id)
        grant_ids.add(version.promotion_grant.id)
        if index == 0:
            if version.supersedes is not None or version.change_note is not None:
                raise ValidationError("initial Direction must not supersede another version")
            continue
        previous = versions[index - 1]
        if version.supersedes != DirectionPredecessor(
            direction_id=previous.direction.id,
            direction_digest=previous.direction_digest,
        ):
            raise ValidationError("Direction version history is not an exact linear chain")
        if version.change_note is None or not version.change_note.strip():
            raise ValidationError("a changed Direction requires a non-empty change note")
        if version.direction.text == previous.direction.text:
            raise ValidationError("a changed Direction must change the exact approved text")
    ledger = DirectionLedger(versions=versions)
    if _text(data["current_direction_id"], "current_direction_id") != ledger.current.direction.id:
        raise ValidationError("Direction ledger current id does not match its latest version")
    return ledger


def _read_unaliased(path: Path, label: str) -> bytes:
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        metadata = os.fstat(descriptor)
        entry = path.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or (metadata.st_dev, metadata.st_ino) != (entry.st_dev, entry.st_ino)
        ):
            raise OSError(f"unsafe {label} identity")
        with os.fdopen(descriptor, "rb", closefd=True) as stream:
            descriptor = None
            content = stream.read()
        entry_after = path.lstat()
        if (metadata.st_dev, metadata.st_ino) != (entry_after.st_dev, entry_after.st_ino):
            raise OSError(f"{label} identity changed while reading")
        return content
    except OSError as error:
        raise DirectionConflictError(f"cannot safely read {label}: {error}") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


class _DirectionLedgerStore:
    def __init__(self, repository: Path) -> None:
        self.repository = repository
        self.path = repository / _LEDGER_PATH

    def exists(self) -> bool:
        try:
            self.path.lstat()
        except FileNotFoundError:
            return False
        except OSError as error:
            raise DirectionConflictError(
                f"cannot inspect approved Direction history: {error}"
            ) from error
        return True

    def load(self) -> DirectionLedger:
        return _ledger_from_json(self.read_json())

    def read_content(self) -> bytes:
        return _read_unaliased(self.path, "approved Direction history")

    def read_json(self) -> object:
        try:
            return strict_json_loads(self.read_content())
        except (UnicodeError, ValueError, StrictJsonError) as error:
            raise ValidationError(f"approved Direction history is invalid: {error}") from error

    def reject_missing_recorded_history(self) -> None:
        if not self.exists() and repository_path_is_recorded(
            self.repository,
            _LEDGER_PATH.as_posix(),
        ):
            raise DirectionConflictError(
                "approved Direction history is recorded by Git but missing from the target"
            )

    def save(self, ledger: DirectionLedger, *, previous_content: bytes | None) -> None:
        writer = PosixAtomicWriter()
        try:
            content = deterministic_document_bytes(ledger)
            intent_directory = git_private_path(
                self.repository,
                "second-mate-direction-intents",
            )
            if previous_content is None:
                writer.create(self.path, content, intent_directory=intent_directory)
            else:
                writer.exchange(
                    self.path,
                    previous_content,
                    content,
                    intent_directory=intent_directory,
                )
        except StateRecoveryError as error:
            if previous_content is None and "already exists" in str(error):
                raise DirectionConflictError(
                    "approved Direction history appeared during initial install"
                ) from error
            if previous_content is not None and "target changed" in str(error):
                raise DirectionConflictError(
                    "approved Direction history changed during append install"
                ) from error
            raise

    def pending_exchange(self) -> tuple[bytes, bytes] | None:
        return pending_atomic_exchange(
            self.path,
            intent_directory=git_private_path(
                self.repository,
                "second-mate-direction-intents",
            ),
        )

    def finish_exchange(self, previous_content: bytes, installed_content: bytes) -> None:
        PosixAtomicWriter().exchange(
            self.path,
            previous_content,
            installed_content,
            intent_directory=git_private_path(
                self.repository,
                "second-mate-direction-intents",
            ),
        )


def _run_state_sha256(repository: Path) -> str | None:
    path = repository / _RUN_STATE_PATH
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError:
        return None
    except OSError as error:
        raise ValidationError(f"cannot safely inspect packet run state: {error}") from error
    try:
        metadata = os.fstat(descriptor)
        entry = path.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or (metadata.st_dev, metadata.st_ino) != (entry.st_dev, entry.st_ino)
        ):
            raise ValidationError("packet run state must be one unaliased regular file")
        with os.fdopen(descriptor, "rb", closefd=True) as stream:
            descriptor = -1
            return hashlib.sha256(stream.read()).hexdigest()
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _has_open_or_pending_run(repository: Path) -> bool:
    pending = repository / _RUN_PENDING_PATH
    try:
        pending.lstat()
    except FileNotFoundError:
        pass
    except OSError as error:
        raise DirectionConflictError(f"cannot inspect pending packet run state: {error}") from error
    else:
        return True
    state_path = repository / _RUN_STATE_PATH
    try:
        state_path.lstat()
    except FileNotFoundError:
        return False
    except OSError as error:
        raise DirectionConflictError(f"cannot inspect packet run state: {error}") from error
    try:
        value = strict_json_loads(_read_unaliased(state_path, "packet run state"))
    except (UnicodeError, ValueError, StrictJsonError) as error:
        raise DirectionConflictError(f"packet run state is not safely closed: {error}") from error
    from second_mate.service import _run_state_from_json

    try:
        state = _run_state_from_json(value)
    except (RuntimeError, ValidationError) as error:
        raise DirectionConflictError(f"packet run state is not safely closed: {error}") from error
    return state.run.phase != "closed" or state.route_status != "completed"


def require_direction_promotion_idle(repository: Path) -> None:
    """Reject approval/promotion while an existing packet run is not safely closed."""
    if _has_open_or_pending_run(repository.resolve()):
        raise DirectionConflictError("an open packet run must close before Direction promotion")


def direction_promotion_recovery_pending(repository: Path) -> bool:
    """Report whether an exact Direction exchange still requires recovery."""
    store = _DirectionLedgerStore(repository.resolve())
    return store.pending_exchange() is not None


@contextmanager
def _direction_lock(repository: Path) -> Iterator[None]:
    try:
        with mutation_lock(repository):
            yield
    except MutationLockBusyError as error:
        raise DirectionConflictError(str(error)) from error


def _revision_fingerprint_with_ledger(
    revision: TargetRevision,
    ledger_content: bytes,
) -> str:
    ledger_path = _LEDGER_PATH.as_posix()
    replaced = False
    facts: list[FileFact] = []
    for fact in revision.files:
        if fact.path != ledger_path:
            facts.append(fact)
            continue
        replaced = True
        facts.append(
            FileFact(
                path=fact.path,
                kind="file",
                sha256=hashlib.sha256(ledger_content).hexdigest(),
                executable=fact.executable,
            )
        )
    if not replaced:
        raise DirectionConflictError("installed Direction history is absent from revision")
    return digest_json(
        {
            "branch": revision.branch,
            "files": [fact.to_json() for fact in facts],
            "head": revision.head,
            "index_sha256": revision.index_sha256,
        }
    )


def _append_version(
    previous: DirectionLedger,
    version: ApprovedDirectionVersion,
) -> DirectionLedger:
    if any(item.direction.id == version.direction.id for item in previous.versions):
        raise DirectionConflictError("an approved Direction id cannot be reused")
    if any(item.approval.id == version.approval.id for item in previous.versions):
        raise DirectionConflictError("a Direction approval id cannot be reused")
    if any(item.promotion_grant.id == version.promotion_grant.id for item in previous.versions):
        raise DirectionConflictError("a Direction promotion grant id cannot be reused")
    expected_predecessor = DirectionPredecessor(
        direction_id=previous.current.direction.id,
        direction_digest=previous.current.direction_digest,
    )
    if version.supersedes != expected_predecessor:
        raise DirectionConflictError(
            "stale Direction candidate does not supersede the current approved version"
        )
    if version.change_note is None or not version.change_note.strip():
        raise ValidationError("a changed Direction requires a non-empty change note")
    if version.direction.text == previous.current.direction.text:
        raise ValidationError("a changed Direction must change the exact approved text")
    return DirectionLedger(versions=(*previous.versions, version))


def prepare_direction(
    repository: Path,
    summary: str,
    *,
    direction_id: str,
    change_note: str | None,
) -> DirectionCandidateEnvelope:
    """Freeze exact Direction text and its current repository basis without writing."""
    root = repository.resolve()
    if repository_path_is_ignored(root, _LEDGER_PATH.as_posix()):
        raise ValidationError("approved Direction project state must not be ignored by Git")
    if not summary.strip():
        raise ValidationError("Direction Summary must be non-empty")
    store = _DirectionLedgerStore(root)
    store.reject_missing_recorded_history()
    predecessor: DirectionPredecessor | None = None
    if store.exists():
        ledger = store.load()
        if any(version.direction.id == direction_id for version in ledger.versions):
            raise DirectionConflictError("an approved Direction id cannot be reused")
        if change_note is None or not change_note.strip():
            raise ValidationError("a changed Direction requires a non-empty change note")
        if summary == ledger.current.direction.text:
            raise ValidationError("a changed Direction must change the exact approved text")
        predecessor = DirectionPredecessor(
            direction_id=ledger.current.direction.id,
            direction_digest=ledger.current.direction_digest,
        )
    elif change_note is not None:
        raise ValidationError("an initial Direction must not carry a change note")
    candidate = DirectionCandidate(
        id=_direction_id(direction_id),
        text=summary,
        supersedes=predecessor,
        change_note=change_note,
    )
    revision = inspect_revision(root)
    return DirectionCandidateEnvelope(
        candidate=candidate,
        digest=digest_json(candidate.to_json()),
        promotion_basis=PromotionBasis(
            target_head=revision.head,
            target_fingerprint=revision.fingerprint,
            run_state_sha256=_run_state_sha256(root),
        ),
    )


def promote_direction(
    repository: Path,
    candidate_data: object,
    approval_data: object | None,
    promotion_grant_data: object | None,
) -> ApprovedDirectionVersion:
    """Persist only a candidate with separate exact approval and write authority."""
    root = repository.resolve()
    candidate = _candidate_envelope_from_json(candidate_data)
    approval = _approval_from_json(approval_data)
    grant = _promotion_grant_from_json(promotion_grant_data)
    if approval.direction_id != candidate.candidate.id:
        raise ValidationError("Direction approval identifies a different candidate")
    if approval.candidate_digest != candidate.digest:
        raise ValidationError("Direction approval digest does not match the exact candidate")
    if grant.candidate_digest != candidate.digest:
        raise ValidationError(
            "promotion grant candidate_digest does not match the prepared candidate"
        )
    expected_basis = candidate.promotion_basis
    if (
        grant.target_head != expected_basis.target_head
        or grant.target_fingerprint != expected_basis.target_fingerprint
        or grant.run_state_sha256 != expected_basis.run_state_sha256
    ):
        raise ValidationError("promotion grant does not match the prepared repository basis")
    direction = Direction(
        id=candidate.candidate.id,
        text=candidate.candidate.text,
        approval=Approval(approved_by=approval.approved_by, approved_at=approval.approved_at),
    )
    version = ApprovedDirectionVersion(
        direction=direction,
        direction_digest=digest_json(direction.to_json()),
        approval=approval,
        promotion_grant=grant,
        supersedes=candidate.candidate.supersedes,
        change_note=candidate.candidate.change_note,
    )
    with _direction_lock(root):
        if _has_open_or_pending_run(root):
            raise DirectionConflictError("an open packet run must close before Direction promotion")
        if repository_path_is_ignored(root, _LEDGER_PATH.as_posix()):
            raise ValidationError("approved Direction project state must not be ignored by Git")
        store = _DirectionLedgerStore(root)
        pending_exchange = store.pending_exchange()
        if pending_exchange is not None:
            previous_content, installed_content = pending_exchange
            try:
                previous = _ledger_from_json(strict_json_loads(previous_content))
            except (UnicodeError, ValueError, StrictJsonError) as error:
                raise DirectionConflictError(
                    f"interrupted Direction exchange displaced invalid history: {error}"
                ) from error
            recovered_ledger = _append_version(previous, version)
            if deterministic_document_bytes(recovered_ledger) != installed_content:
                raise DirectionConflictError(
                    "interrupted Direction exchange does not match the exact candidate"
                )
            current_revision = inspect_revision(root)
            if (
                current_revision.head != expected_basis.target_head
                or _revision_fingerprint_with_ledger(current_revision, previous_content)
                != expected_basis.target_fingerprint
                or _run_state_sha256(root) != expected_basis.run_state_sha256
            ):
                raise DirectionConflictError(
                    "revision drift invalidated interrupted Direction recovery"
                )
            store.finish_exchange(previous_content, installed_content)
            return version
        revision = inspect_revision(root)
        if (
            revision.head != expected_basis.target_head
            or revision.fingerprint != expected_basis.target_fingerprint
            or _run_state_sha256(root) != expected_basis.run_state_sha256
        ):
            raise DirectionConflictError("revision drift invalidated Direction promotion authority")
        store.reject_missing_recorded_history()
        current_content = store.read_content() if store.exists() else None
        current_ledger = (
            _ledger_from_json(strict_json_loads(current_content)) if current_content else None
        )
        if current_ledger is None:
            if (
                candidate.candidate.supersedes is not None
                or candidate.candidate.change_note is not None
            ):
                raise DirectionConflictError("stale Direction candidate expects missing history")
            ledger = DirectionLedger(versions=(version,))
        else:
            ledger = _append_version(current_ledger, version)
        store.save(ledger, previous_content=current_content)
    return version


def find_direction_version(
    repository: Path,
    direction_id: str | None = None,
) -> DirectionVersionLookup | None:
    """Find a validated Direction version without treating absence as malformed state."""
    store = _DirectionLedgerStore(repository.resolve())
    store.reject_missing_recorded_history()
    if not store.exists():
        return None
    ledger = store.load()
    if direction_id is None:
        return DirectionVersionLookup(version=ledger.current, is_current=True)
    wanted = _direction_id(direction_id)
    for version in ledger.versions:
        if version.direction.id == wanted:
            return DirectionVersionLookup(
                version=version,
                is_current=version.direction.id == ledger.current.direction.id,
            )
    return None


def load_direction(repository: Path, direction_id: str | None = None) -> Direction:
    """Load one validated approved Direction, defaulting to the current version."""
    ledger = _DirectionLedgerStore(repository.resolve()).load()
    if direction_id is None:
        return ledger.current.direction
    wanted = _direction_id(direction_id)
    for version in ledger.versions:
        if version.direction.id == wanted:
            return version.direction
    raise ValidationError(f"approved Direction {direction_id} does not exist")
