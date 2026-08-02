"""Local handoff from an external Rumble summary to approved Direction state."""

from __future__ import annotations

import fcntl
import json
import os
import re
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
from second_mate.repository import git_private_path, repository_root
from second_mate.store import PosixAtomicWriter, deterministic_document_bytes

_DIRECTION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_LEDGER_PATH = Path(".second-mate/directions.json")


class DirectionConflictError(RuntimeError):
    """A promotion would replace or branch immutable Direction history."""


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


def _exact_keys(value: dict[str, object], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValidationError(f"{label} fields do not match schema version 1")


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be a non-empty string")
    return value


def _sha256(value: object, label: str) -> str:
    digest = _text(value, label)
    if not _SHA256.fullmatch(digest):
        raise ValidationError(f"{label} must be a lowercase SHA-256 digest")
    return digest


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
class DirectionCandidateEnvelope:
    candidate: DirectionCandidate
    digest: str

    def to_json(self) -> JsonObject:
        return {
            "candidate": self.candidate.to_json(),
            "candidate_digest": self.digest,
            "schema_version": 1,
        }


@dataclass(frozen=True, slots=True)
class DirectionApproval:
    id: str
    direction_id: str
    candidate_digest: str
    approved_by: str
    approved_at: str

    def to_json(self) -> JsonObject:
        return {
            "approved_at": self.approved_at,
            "approved_by": self.approved_by,
            "candidate_digest": self.candidate_digest,
            "decision": "approved",
            "direction_id": self.direction_id,
            "id": self.id,
            "schema_version": 1,
        }


@dataclass(frozen=True, slots=True)
class ApprovedDirectionVersion:
    direction: Direction
    direction_digest: str
    approval: DirectionApproval
    supersedes: DirectionPredecessor | None
    change_note: str | None

    def to_json(self) -> JsonObject:
        return {
            "approval": self.approval.to_json(),
            "change_note": self.change_note,
            "direction": self.direction.to_json(),
            "direction_digest": self.direction_digest,
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
            "versions": [item.to_json() for item in self.versions],
        }


def _predecessor_from_json(value: object) -> DirectionPredecessor | None:
    if value is None:
        return None
    data = _object(value, "candidate supersedes")
    _exact_keys(data, {"direction_id", "direction_digest"}, "candidate supersedes")
    return DirectionPredecessor(
        direction_id=_direction_id(_text(data["direction_id"], "supersedes direction_id")),
        direction_digest=_sha256(data["direction_digest"], "supersedes direction_digest"),
    )


def _candidate_envelope_from_json(value: object) -> DirectionCandidateEnvelope:
    data = _object(value, "Direction candidate envelope")
    _exact_keys(
        data,
        {"schema_version", "candidate", "candidate_digest"},
        "Direction candidate envelope",
    )
    if data["schema_version"] != 1:
        raise ValidationError("Direction candidate envelope schema_version must be 1")
    candidate_data = _object(data["candidate"], "Direction candidate")
    _exact_keys(
        candidate_data,
        {"schema_version", "id", "text", "supersedes", "change_note"},
        "Direction candidate",
    )
    if candidate_data["schema_version"] != 1:
        raise ValidationError("Direction candidate schema_version must be 1")
    change_note_raw = candidate_data["change_note"]
    if change_note_raw is not None and not isinstance(change_note_raw, str):
        raise ValidationError("Direction candidate change_note must be a string or null")
    candidate = DirectionCandidate(
        id=_direction_id(_text(candidate_data["id"], "Direction candidate id")),
        text=_text(candidate_data["text"], "Direction candidate text"),
        supersedes=_predecessor_from_json(candidate_data["supersedes"]),
        change_note=change_note_raw,
    )
    stored_digest = _sha256(data["candidate_digest"], "Direction candidate digest")
    if digest_json(candidate.to_json()) != stored_digest:
        raise ValidationError("Direction candidate digest does not match its exact content")
    return DirectionCandidateEnvelope(candidate=candidate, digest=stored_digest)


def _approval_from_json(value: object | None) -> DirectionApproval:
    if value is None:
        raise ValidationError("explicit Direction approval is required before promotion")
    data = _object(value, "Direction approval")
    _exact_keys(
        data,
        {
            "schema_version",
            "id",
            "decision",
            "direction_id",
            "candidate_digest",
            "approved_by",
            "approved_at",
        },
        "Direction approval",
    )
    if data["schema_version"] != 1:
        raise ValidationError("Direction approval schema_version must be 1")
    if data["decision"] != "approved":
        raise ValidationError("Direction approval decision must be approved")
    direction_id = _direction_id(_text(data["direction_id"], "Direction approval direction_id"))
    candidate_digest = _sha256(data["candidate_digest"], "Direction approval candidate_digest")
    return DirectionApproval(
        id=_direction_id(_text(data["id"], "Direction approval id")),
        direction_id=direction_id,
        candidate_digest=candidate_digest,
        approved_by=_text(data["approved_by"], "Direction approval approved_by"),
        approved_at=_text(data["approved_at"], "Direction approval approved_at"),
    )


def _version_from_json(value: object) -> ApprovedDirectionVersion:
    data = _object(value, "approved Direction version")
    _exact_keys(
        data,
        {"approval", "change_note", "direction", "direction_digest", "supersedes"},
        "approved Direction version",
    )
    approval = _approval_from_json(data["approval"])
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
        raise ValidationError("Direction approval record disagrees with the approved Direction")
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
    if data["schema_version"] != 1:
        raise ValidationError("Direction ledger schema_version must be 1")
    versions_raw = data["versions"]
    if not isinstance(versions_raw, list) or not versions_raw:
        raise ValidationError("Direction ledger must contain approved versions")
    versions = tuple(_version_from_json(item) for item in versions_raw)
    direction_ids: set[str] = set()
    approval_ids: set[str] = set()
    for index, version in enumerate(versions):
        if version.direction.id in direction_ids:
            raise ValidationError("Direction ledger contains a duplicate Direction id")
        if version.approval.id in approval_ids:
            raise ValidationError("Direction ledger contains a duplicate approval id")
        direction_ids.add(version.direction.id)
        approval_ids.add(version.approval.id)
        if index == 0:
            if version.supersedes is not None or version.change_note is not None:
                raise ValidationError("initial Direction must not supersede another version")
            continue
        previous = versions[index - 1]
        expected_predecessor = DirectionPredecessor(
            direction_id=previous.direction.id,
            direction_digest=previous.direction_digest,
        )
        if version.supersedes != expected_predecessor:
            raise ValidationError("Direction version history is not an exact linear chain")
        if version.change_note is None or not version.change_note.strip():
            raise ValidationError("a changed Direction requires a non-empty change note")
        if version.direction.text == previous.direction.text:
            raise ValidationError("a changed Direction must change the exact approved text")
    ledger = DirectionLedger(versions=versions)
    if _text(data["current_direction_id"], "current_direction_id") != ledger.current.direction.id:
        raise ValidationError("Direction ledger current id does not match its latest version")
    return ledger


class _DirectionLedgerStore:
    def __init__(self, repository: Path) -> None:
        self.path = repository / _LEDGER_PATH
        self.writer = PosixAtomicWriter()

    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> DirectionLedger:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ValidationError(f"cannot read Direction ledger: {error}") from error
        return _ledger_from_json(raw)

    def save(self, previous: DirectionLedger | None, ledger: DirectionLedger) -> None:
        if previous is None:
            if self.path.exists():
                raise DirectionConflictError("approved Direction history appeared during promotion")
        else:
            try:
                current = self.path.read_bytes()
            except OSError as error:
                raise DirectionConflictError(
                    "approved Direction history disappeared during promotion"
                ) from error
            if current != deterministic_document_bytes(previous):
                raise DirectionConflictError("approved Direction history changed during promotion")
        self.writer.write(self.path, deterministic_document_bytes(ledger))


@contextmanager
def _direction_lock(repository: Path) -> Iterator[None]:
    lock_path = git_private_path(repository, "second-mate-direction.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def prepare_direction(
    repository: Path,
    summary: str,
    *,
    direction_id: str,
    change_note: str | None,
) -> DirectionCandidateEnvelope:
    """Freeze an editable summary into a read-only, approval-ready candidate."""
    root = repository_root(repository)
    if not summary.strip():
        raise ValidationError("Direction Summary must be non-empty")
    store = _DirectionLedgerStore(root)
    predecessor: DirectionPredecessor | None = None
    if store.exists():
        ledger = store.load()
        if any(item.direction.id == direction_id for item in ledger.versions):
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
    return DirectionCandidateEnvelope(candidate=candidate, digest=digest_json(candidate.to_json()))


def promote_direction(
    repository: Path,
    candidate_data: object,
    approval_data: object | None,
) -> ApprovedDirectionVersion:
    """Persist only a separately and exactly approved Direction candidate."""
    root = repository_root(repository)
    candidate = _candidate_envelope_from_json(candidate_data)
    approval = _approval_from_json(approval_data)
    if approval.direction_id != candidate.candidate.id:
        raise ValidationError("Direction approval identifies a different candidate")
    if approval.candidate_digest != candidate.digest:
        raise ValidationError("Direction approval digest does not match the exact candidate")
    direction = Direction(
        id=candidate.candidate.id,
        text=candidate.candidate.text,
        approval=Approval(
            approved_by=approval.approved_by,
            approved_at=approval.approved_at,
        ),
    )
    with _direction_lock(root):
        store = _DirectionLedgerStore(root)
        previous = store.load() if store.exists() else None
        if previous is None:
            if (
                candidate.candidate.supersedes is not None
                or candidate.candidate.change_note is not None
            ):
                raise DirectionConflictError(
                    "stale Direction candidate expects history that does not exist"
                )
        else:
            if any(item.direction.id == direction.id for item in previous.versions):
                raise DirectionConflictError("an approved Direction id cannot be reused")
            if any(item.approval.id == approval.id for item in previous.versions):
                raise DirectionConflictError("an explicit Direction approval id cannot be reused")
            expected_predecessor = DirectionPredecessor(
                direction_id=previous.current.direction.id,
                direction_digest=previous.current.direction_digest,
            )
            if candidate.candidate.supersedes != expected_predecessor:
                raise DirectionConflictError(
                    "stale Direction candidate does not supersede the current approved version"
                )
            if (
                candidate.candidate.change_note is None
                or not candidate.candidate.change_note.strip()
            ):
                raise ValidationError("a changed Direction requires a non-empty change note")
            if candidate.candidate.text == previous.current.direction.text:
                raise ValidationError("a changed Direction must change the exact approved text")
        version = ApprovedDirectionVersion(
            direction=direction,
            direction_digest=digest_json(direction.to_json()),
            approval=approval,
            supersedes=candidate.candidate.supersedes,
            change_note=candidate.candidate.change_note,
        )
        ledger = DirectionLedger(
            versions=(version,) if previous is None else (*previous.versions, version)
        )
        store.save(previous, ledger)
    return version


def load_direction(repository: Path, direction_id: str | None = None) -> Direction:
    """Load one validated approved Direction, defaulting to the current version."""
    root = repository_root(repository)
    ledger = _DirectionLedgerStore(root).load()
    if direction_id is None:
        return ledger.current.direction
    wanted = _direction_id(direction_id)
    for version in ledger.versions:
        if version.direction.id == wanted:
            return version.direction
    raise ValidationError(f"approved Direction {direction_id} does not exist")
