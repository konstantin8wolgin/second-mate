"""Local handoff from an external Rumble summary to approved Direction state."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import secrets
import stat
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from second_mate.domain import (
    STATE_PATH,
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
    inspect_revision,
    mutation_lock,
    repository_path_is_ignored,
    repository_path_is_recorded,
    repository_root,
)
from second_mate.store import StrictJsonError, deterministic_document_bytes, strict_json_loads

_DIRECTION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_LEDGER_PATH = Path(".second-mate/directions.json")
_ALLOWED_PATHS = (".second-mate/directions.json",)
_ALLOWED_EFFECTS = ("direction_ledger_write",)
_STOP_CONDITIONS = ("revision_drift", "direction_history_drift")
_RENAME_NOREPLACE = 1
_RENAME_EXCHANGE = 2


class DirectionConflictError(RuntimeError):
    """A promotion would replace or branch immutable Direction history."""


class _ExchangeRecoveryError(DirectionConflictError):
    """An exchange could not safely restore the displaced concurrent entry."""


@dataclass(frozen=True, slots=True)
class _PathEntry:
    kind: str
    device: int
    inode: int
    mode: int
    content: bytes


@dataclass(frozen=True, slots=True)
class _OwnedTemporary:
    name: str
    entry: _PathEntry


def _same_revision_except(
    current: TargetRevision,
    expected: TargetRevision,
    excluded_paths: frozenset[str],
) -> bool:
    current_facts = tuple(item for item in current.files if item.path not in excluded_paths)
    expected_facts = tuple(item for item in expected.files if item.path not in excluded_paths)
    return current.head == expected.head and current_facts == expected_facts


def _matches_installed_ledger(
    current: TargetRevision,
    before: TargetRevision,
    ledger_content: bytes,
    temporary_path: str | None = None,
    temporary_entry: _PathEntry | None = None,
) -> bool:
    excluded_paths = {_LEDGER_PATH.as_posix()}
    if temporary_path is not None:
        excluded_paths.add(temporary_path)
    excluded = frozenset(excluded_paths)
    if not _same_revision_except(current, before, excluded):
        return False
    ledger_facts = tuple(item for item in current.files if item.path == _LEDGER_PATH.as_posix())
    if ledger_facts != (
        FileFact(
            path=_LEDGER_PATH.as_posix(),
            kind="file",
            sha256=hashlib.sha256(ledger_content).hexdigest(),
            executable=False,
        ),
    ):
        return False
    if temporary_path is None:
        return True
    if temporary_entry is None or temporary_entry.kind != "file":
        return False
    temporary_facts = tuple(item for item in current.files if item.path == temporary_path)
    return temporary_facts == (
        FileFact(
            path=temporary_path,
            kind="file",
            sha256=hashlib.sha256(temporary_entry.content).hexdigest(),
            executable=bool(temporary_entry.mode & stat.S_IXUSR),
        ),
    )


def _inspect_direction_revision(
    repository: Path,
    store: _DirectionLedgerStore | None = None,
) -> TargetRevision:
    """Include durable run state in the revision that authorizes Direction writes."""
    revision = inspect_revision(repository)
    state_fact, _ = (store or _DirectionLedgerStore(repository))._run_state_snapshot()
    if state_fact is None:
        return revision
    facts = tuple(sorted((*revision.files, state_fact), key=lambda item: item.path))
    fingerprint = digest_json(
        {
            "files": [item.to_json() for item in facts],
            "head": revision.head,
        }
    )
    return TargetRevision(head=revision.head, fingerprint=fingerprint, files=facts)


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


def _schema_one(value: object, label: str) -> None:
    if type(value) is not int or value != 1:
        raise ValidationError(f"{label} schema_version must be the integer 1")


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be a non-empty string")
    return value


def _sha256(value: object, label: str) -> str:
    digest = _text(value, label)
    if not _SHA256.fullmatch(digest):
        raise ValidationError(f"{label} must be a lowercase SHA-256 digest")
    return digest


def _strings(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValidationError(f"{label} must be a list of non-empty strings")
    result = tuple(cast(list[str], value))
    if len(result) != len(set(result)):
        raise ValidationError(f"{label} must contain no duplicates")
    return result


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
    target_root: str
    target_head: str
    target_fingerprint: str

    def to_json(self) -> JsonObject:
        return {
            "target_fingerprint": self.target_fingerprint,
            "target_head": self.target_head,
            "target_root": self.target_root,
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
class PromotionGrant:
    id: str
    granted_by: str
    granted_at: str
    candidate_digest: str
    target_root: str
    target_head: str
    target_fingerprint: str
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
            "schema_version": 1,
            "stop_conditions": list(self.stop_conditions),
            "target_fingerprint": self.target_fingerprint,
            "target_head": self.target_head,
            "target_root": self.target_root,
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
    basis_data = _object(data["promotion_basis"], "Direction promotion basis")
    _exact_keys(
        basis_data,
        {"target_root", "target_head", "target_fingerprint"},
        "Direction promotion basis",
    )
    target_root = _text(basis_data["target_root"], "promotion basis target_root")
    if not Path(target_root).is_absolute():
        raise ValidationError("promotion basis target_root must be absolute")
    basis = PromotionBasis(
        target_root=target_root,
        target_head=_text(basis_data["target_head"], "promotion basis target_head"),
        target_fingerprint=_sha256(
            basis_data["target_fingerprint"], "promotion basis target_fingerprint"
        ),
    )
    return DirectionCandidateEnvelope(
        candidate=candidate,
        digest=stored_digest,
        promotion_basis=basis,
    )


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
    _schema_one(data["schema_version"], "Direction approval")
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
            "target_root",
            "target_head",
            "target_fingerprint",
            "allowed_paths",
            "allowed_effects",
            "stop_conditions",
        },
        "Direction promotion grant",
    )
    _schema_one(data["schema_version"], "Direction promotion grant")
    target_root = _text(data["target_root"], "promotion grant target_root")
    if not Path(target_root).is_absolute():
        raise ValidationError("promotion grant target_root must be absolute")
    grant = PromotionGrant(
        id=_direction_id(_text(data["id"], "promotion grant id")),
        granted_by=_text(data["granted_by"], "promotion grant granted_by"),
        granted_at=_text(data["granted_at"], "promotion grant granted_at"),
        candidate_digest=_sha256(data["candidate_digest"], "promotion grant candidate_digest"),
        target_root=target_root,
        target_head=_text(data["target_head"], "promotion grant target_head"),
        target_fingerprint=_sha256(
            data["target_fingerprint"], "promotion grant target_fingerprint"
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
    promotion_grant = _promotion_grant_from_json(data["promotion_grant"])
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
    if promotion_grant.candidate_digest != approval.candidate_digest:
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
        promotion_grant=promotion_grant,
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
    promotion_grant_ids: set[str] = set()
    for index, version in enumerate(versions):
        if version.direction.id in direction_ids:
            raise ValidationError("Direction ledger contains a duplicate Direction id")
        if version.approval.id in approval_ids:
            raise ValidationError("Direction ledger contains a duplicate approval id")
        if version.promotion_grant.id in promotion_grant_ids:
            raise ValidationError("Direction ledger contains a duplicate promotion grant id")
        direction_ids.add(version.direction.id)
        approval_ids.add(version.approval.id)
        promotion_grant_ids.add(version.promotion_grant.id)
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
        self.repository = repository
        self.path = repository / _LEDGER_PATH

    def exists(self) -> bool:
        try:
            parent_metadata = (self.repository / ".second-mate").lstat()
        except FileNotFoundError:
            return False
        if not stat.S_ISDIR(parent_metadata.st_mode):
            return False
        try:
            self.path.lstat()
        except FileNotFoundError:
            return False
        return True

    def reject_missing_recorded_history(self) -> None:
        if not self.exists() and repository_path_is_recorded(
            self.repository,
            _LEDGER_PATH.as_posix(),
        ):
            raise DirectionConflictError(
                "approved Direction history is recorded by Git but missing from the target"
            )

    @staticmethod
    def _rename_paths(
        state_descriptor: int,
        left: str,
        right: str,
        *,
        flags: int,
    ) -> None:
        """Use one verified Linux rename operation relative to the pinned state fd."""
        library = ctypes.CDLL(None, use_errno=True)
        try:
            renameat2 = library.renameat2
        except AttributeError as error:
            raise ValidationError(
                "atomic Direction history exchange is unavailable on this platform"
            ) from error
        renameat2.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        renameat2.restype = ctypes.c_int
        if (
            renameat2(
                state_descriptor,
                os.fsencode(left),
                state_descriptor,
                os.fsencode(right),
                flags,
            )
            != 0
        ):
            error_number = ctypes.get_errno()
            raise OSError(error_number, os.strerror(error_number))

    @classmethod
    def _exchange_paths(cls, state_descriptor: int, left: str, right: str) -> None:
        """Atomically exchange two existing names in the verified Linux environment."""
        cls._rename_paths(
            state_descriptor,
            left,
            right,
            flags=_RENAME_EXCHANGE,
        )

    @classmethod
    def _move_path_no_replace(
        cls,
        state_descriptor: int,
        source: str,
        destination: str,
    ) -> None:
        """Atomically move one name only when the destination is absent."""
        cls._rename_paths(
            state_descriptor,
            source,
            destination,
            flags=_RENAME_NOREPLACE,
        )

    @staticmethod
    def _entry_kind(mode: int) -> str:
        if stat.S_ISREG(mode):
            return "file"
        if stat.S_ISLNK(mode):
            return "symlink"
        if stat.S_ISDIR(mode):
            return "directory"
        return "other"

    @classmethod
    def _path_entry(cls, state_descriptor: int, name: str) -> _PathEntry:
        before = os.stat(name, dir_fd=state_descriptor, follow_symlinks=False)
        kind = cls._entry_kind(before.st_mode)
        content = b""
        if kind == "file":
            descriptor = os.open(
                name,
                os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW,
                dir_fd=state_descriptor,
            )
            try:
                opened = os.fstat(descriptor)
                if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
                    before.st_dev,
                    before.st_ino,
                ):
                    raise DirectionConflictError(
                        "Direction entry identity changed while it was inspected"
                    )
                with os.fdopen(descriptor, "rb", closefd=False) as stream:
                    content = stream.read()
            finally:
                os.close(descriptor)
        elif kind == "symlink":
            content = os.fsencode(os.readlink(name, dir_fd=state_descriptor))
        after = os.stat(name, dir_fd=state_descriptor, follow_symlinks=False)
        if cls._entry_kind(after.st_mode) != kind or (
            after.st_dev,
            after.st_ino,
            stat.S_IMODE(after.st_mode),
        ) != (before.st_dev, before.st_ino, stat.S_IMODE(before.st_mode)):
            raise DirectionConflictError("Direction entry identity changed while it was inspected")
        return _PathEntry(
            kind=kind,
            device=after.st_dev,
            inode=after.st_ino,
            mode=stat.S_IMODE(after.st_mode),
            content=content,
        )

    @classmethod
    def _exchange_if_current(
        cls,
        state_descriptor: int,
        replacement: _OwnedTemporary,
        target: str,
        *,
        expected_displaced: _PathEntry,
    ) -> bool:
        try:
            cls._exchange_paths(state_descriptor, replacement.name, target)
        except OSError as error:
            raise DirectionConflictError("atomic Direction history exchange failed") from error
        try:
            displaced = cls._path_entry(state_descriptor, replacement.name)
        except Exception:
            displaced = None
        try:
            installed = cls._path_entry(state_descriptor, target)
        except Exception:
            installed = None
        if displaced == expected_displaced and installed == replacement.entry:
            return True
        try:
            cls._exchange_paths(state_descriptor, replacement.name, target)
            os.fsync(state_descriptor)
            restored_target = cls._path_entry(state_descriptor, target)
            recovered_temporary = cls._path_entry(state_descriptor, replacement.name)
        except Exception as error:
            raise _ExchangeRecoveryError(
                "atomic exchange was invalidated; displaced history was retained for recovery"
            ) from error
        if displaced is None or restored_target != displaced:
            raise _ExchangeRecoveryError(
                "atomic exchange was invalidated; displaced history was retained for recovery"
            )
        if recovered_temporary != replacement.entry:
            raise _ExchangeRecoveryError(
                "atomic exchange was invalidated; a late entry was retained for recovery"
            )
        return False

    @staticmethod
    def _assert_repository_root_attached(
        parent_descriptor: int,
        root_descriptor: int,
        root_name: str,
    ) -> None:
        try:
            path_metadata = os.stat(
                root_name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        except OSError as error:
            raise DirectionConflictError(
                "repository root is no longer attached to its authorized path"
            ) from error
        opened_metadata = os.fstat(root_descriptor)
        if not stat.S_ISDIR(path_metadata.st_mode) or (
            path_metadata.st_dev,
            path_metadata.st_ino,
        ) != (opened_metadata.st_dev, opened_metadata.st_ino):
            raise DirectionConflictError(
                "repository root is no longer attached to its authorized path"
            )

    @staticmethod
    def _assert_state_directory_attached(
        root_descriptor: int,
        state_descriptor: int,
    ) -> None:
        try:
            path_metadata = os.stat(
                ".second-mate",
                dir_fd=root_descriptor,
                follow_symlinks=False,
            )
        except OSError as error:
            raise DirectionConflictError(
                "Direction state directory is no longer attached to the target"
            ) from error
        opened_metadata = os.fstat(state_descriptor)
        if not stat.S_ISDIR(path_metadata.st_mode) or (
            path_metadata.st_dev,
            path_metadata.st_ino,
        ) != (opened_metadata.st_dev, opened_metadata.st_ino):
            raise DirectionConflictError(
                "Direction state directory is no longer attached to the target"
            )

    def _assert_sink_attached(
        self,
        parent_descriptor: int,
        root_descriptor: int,
        state_descriptor: int,
    ) -> None:
        self._assert_repository_root_attached(
            parent_descriptor,
            root_descriptor,
            self.repository.name,
        )
        self._assert_state_directory_attached(root_descriptor, state_descriptor)

    @contextmanager
    def _state_directory(self, *, create: bool) -> Iterator[tuple[int, int, int]]:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        if self.repository.parent == self.repository:
            raise ValidationError("repository root must have an attachable parent directory")
        parent_descriptor = os.open(self.repository.parent, directory_flags)
        root_descriptor: int | None = None
        state_descriptor: int | None = None
        try:
            try:
                root_descriptor = os.open(
                    self.repository.name,
                    directory_flags,
                    dir_fd=parent_descriptor,
                )
            except OSError as error:
                raise ValidationError(
                    "repository root must remain a real directory, not a symlink"
                ) from error
            if create:
                try:
                    os.mkdir(".second-mate", mode=0o755, dir_fd=root_descriptor)
                    os.fsync(root_descriptor)
                except FileExistsError:
                    pass
            try:
                state_descriptor = os.open(
                    ".second-mate",
                    directory_flags,
                    dir_fd=root_descriptor,
                )
            except OSError as error:
                raise ValidationError(
                    "Direction state directory must be a real directory, not a symlink"
                ) from error
            self._assert_sink_attached(
                parent_descriptor,
                root_descriptor,
                state_descriptor,
            )
            yield parent_descriptor, root_descriptor, state_descriptor
        finally:
            if state_descriptor is not None:
                os.close(state_descriptor)
            if root_descriptor is not None:
                os.close(root_descriptor)
            os.close(parent_descriptor)

    @classmethod
    def _read_content_and_mode(
        cls,
        state_descriptor: int,
        name: str = "directions.json",
    ) -> tuple[bytes, int]:
        entry = cls._regular_entry(state_descriptor, name)
        return entry.content, entry.mode

    @classmethod
    def _regular_entry(
        cls,
        state_descriptor: int,
        name: str = "directions.json",
    ) -> _PathEntry:
        try:
            entry = cls._path_entry(state_descriptor, name)
        except (OSError, DirectionConflictError) as error:
            raise ValidationError("Direction ledger must be a real file, not a symlink") from error
        if entry.kind == "symlink":
            raise ValidationError("Direction ledger must be a real file, not a symlink")
        if entry.kind != "file":
            raise ValidationError("Direction ledger must be a regular file")
        return entry

    @classmethod
    def _read_content(cls, state_descriptor: int, name: str = "directions.json") -> bytes:
        return cls._read_content_and_mode(state_descriptor, name)[0]

    @staticmethod
    def _reject_legacy_temporary_symlink(state_descriptor: int) -> None:
        try:
            metadata = os.stat(
                "directions.json.next",
                dir_fd=state_descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return
        if stat.S_ISLNK(metadata.st_mode):
            raise ValidationError("Direction temporary path must not be a symlink")

    @classmethod
    def _cleanup_failed_temporary(
        cls,
        state_descriptor: int,
        temporary: str,
        owned_identity: tuple[int, int],
    ) -> None:
        """Delete a failed temp only after atomically quarantining its owned inode."""
        quarantine = f".directions.json.{secrets.token_hex(12)}.failed"
        try:
            cls._move_path_no_replace(state_descriptor, temporary, quarantine)
            os.fsync(state_descriptor)
        except Exception:
            # Absence, an occupied quarantine name, or an unavailable atomic
            # move leaves the original path untouched for explicit recovery.
            return
        try:
            quarantined = cls._path_entry(state_descriptor, quarantine)
        except Exception:
            return
        if (
            quarantined.kind == "file"
            and (
                quarantined.device,
                quarantined.inode,
            )
            == owned_identity
        ):
            with suppress(Exception):
                cls._discard_if_exact(state_descriptor, quarantine, quarantined)
            return
        try:
            cls._move_path_no_replace(state_descriptor, quarantine, temporary)
            os.fsync(state_descriptor)
        except Exception:
            # An unowned entry remains under the quarantine name if its
            # original name cannot be restored without replacing another.
            return

    @classmethod
    def _write_temporary(
        cls,
        state_descriptor: int,
        content: bytes,
        *,
        mode: int = 0o644,
    ) -> _OwnedTemporary:
        temporary = f".directions.json.{secrets.token_hex(12)}.next"
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                mode,
                dir_fd=state_descriptor,
            )
        except FileExistsError as error:
            raise DirectionConflictError(
                "secure Direction temporary path already exists"
            ) from error
        owned_identity: tuple[int, int] | None = None
        try:
            opened_metadata = os.fstat(descriptor)
            owned_identity = (opened_metadata.st_dev, opened_metadata.st_ino)
            os.fchmod(descriptor, mode)
            with os.fdopen(descriptor, "wb", closefd=False) as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            metadata = os.fstat(descriptor)
            owned = _OwnedTemporary(
                name=temporary,
                entry=_PathEntry(
                    kind="file",
                    device=metadata.st_dev,
                    inode=metadata.st_ino,
                    mode=stat.S_IMODE(metadata.st_mode),
                    content=content,
                ),
            )
        except OSError as error:
            if owned_identity is not None:
                cls._cleanup_failed_temporary(
                    state_descriptor,
                    temporary,
                    owned_identity,
                )
            raise DirectionConflictError(
                "cannot durably write secure Direction temporary file"
            ) from error
        except BaseException:
            if owned_identity is not None:
                cls._cleanup_failed_temporary(
                    state_descriptor,
                    temporary,
                    owned_identity,
                )
            raise
        finally:
            with suppress(OSError):
                os.close(descriptor)
        return owned

    def load(self) -> DirectionLedger:
        try:
            with self._state_directory(create=False) as (
                parent_descriptor,
                root_descriptor,
                state_descriptor,
            ):
                raw = strict_json_loads(self._read_content(state_descriptor).decode("utf-8"))
                self._assert_sink_attached(
                    parent_descriptor,
                    root_descriptor,
                    state_descriptor,
                )
        except (OSError, UnicodeError, json.JSONDecodeError, StrictJsonError) as error:
            raise ValidationError(f"cannot read Direction ledger: {error}") from error
        return _ledger_from_json(raw)

    def _run_state_snapshot(self) -> tuple[FileFact | None, bool]:
        try:
            state_directory_metadata = (self.repository / ".second-mate").lstat()
        except FileNotFoundError:
            return None, False
        if not stat.S_ISDIR(state_directory_metadata.st_mode):
            raise ValidationError(
                "Direction state directory must be a real directory, not a symlink"
            )
        with self._state_directory(create=False) as (
            parent_descriptor,
            root_descriptor,
            state_descriptor,
        ):
            try:
                os.stat(
                    "state.json.pending",
                    dir_fd=state_descriptor,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                pass
            else:
                raise DirectionConflictError(
                    "a pending run-state close must recover before Direction promotion"
                )
            try:
                entry = self._path_entry(state_descriptor, "state.json")
            except FileNotFoundError:
                self._assert_sink_attached(
                    parent_descriptor,
                    root_descriptor,
                    state_descriptor,
                )
                return None, False
            except (OSError, DirectionConflictError) as error:
                raise ValidationError("run state must be a real file, not a symlink") from error
            if entry.kind == "symlink":
                raise ValidationError("run state must be a real file, not a symlink")
            if entry.kind != "file":
                raise ValidationError("run state must be a regular file")
            try:
                raw = strict_json_loads(entry.content.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError, StrictJsonError) as error:
                raise ValidationError(f"cannot read run state: {error}") from error
            from second_mate.service import run_state_from_json

            state = run_state_from_json(raw)
            self._assert_sink_attached(
                parent_descriptor,
                root_descriptor,
                state_descriptor,
            )
        return (
            FileFact(
                path=STATE_PATH,
                kind="file",
                sha256=hashlib.sha256(entry.content).hexdigest(),
                executable=bool(entry.mode & stat.S_IXUSR),
            ),
            not state.closed,
        )

    def has_open_run(self) -> bool:
        _, is_open = self._run_state_snapshot()
        return is_open

    @staticmethod
    def _discard_temporary(state_descriptor: int, temporary: str) -> None:
        try:
            os.unlink(temporary, dir_fd=state_descriptor)
        except FileNotFoundError:
            return
        os.fsync(state_descriptor)

    @classmethod
    def _discard_if_exact(
        cls,
        state_descriptor: int,
        name: str,
        expected: _PathEntry,
    ) -> None:
        try:
            current = cls._path_entry(state_descriptor, name)
        except Exception as error:
            raise _ExchangeRecoveryError(
                "unexpected Direction entry was retained instead of being deleted"
            ) from error
        if current != expected:
            raise _ExchangeRecoveryError(
                "unexpected Direction entry was retained instead of being deleted"
            )
        cls._discard_temporary(state_descriptor, name)

    @classmethod
    def _remove_initial_install(
        cls,
        state_descriptor: int,
        installed: _PathEntry,
        installation_temporary: _OwnedTemporary,
    ) -> None:
        quarantine = f".directions.json.{secrets.token_hex(12)}.rollback"
        try:
            cls._move_path_no_replace(
                state_descriptor,
                "directions.json",
                quarantine,
            )
            os.fsync(state_descriptor)
        except OSError as error:
            raise _ExchangeRecoveryError(
                "initial Direction rollback could not quarantine the final entry"
            ) from error
        try:
            quarantined = cls._path_entry(state_descriptor, quarantine)
        except Exception as error:
            raise _ExchangeRecoveryError(
                "initial Direction rollback retained an unverified final entry"
            ) from error

        if quarantined == installed:
            cls._discard_if_exact(state_descriptor, quarantine, quarantined)
            return

        try:
            source = cls._path_entry(state_descriptor, installation_temporary.name)
        except Exception:
            source = None
        if source == quarantined and source != installation_temporary.entry:
            # The link operation duplicated a substituted source. Removing this
            # quarantined link restores initial absence while the source name
            # retains the unowned object exactly.
            cls._discard_if_exact(state_descriptor, quarantine, quarantined)
            return

        try:
            cls._move_path_no_replace(
                state_descriptor,
                quarantine,
                "directions.json",
            )
            os.fsync(state_descriptor)
            restored = cls._path_entry(state_descriptor, "directions.json")
        except Exception as error:
            raise _ExchangeRecoveryError(
                "a concurrent final Direction entry was retained for recovery"
            ) from error
        if restored != quarantined:
            raise _ExchangeRecoveryError(
                "a concurrent final Direction entry changed while it was restored"
            )
        raise DirectionConflictError(
            "a concurrent final Direction entry was restored during rollback"
        )

    def _rollback_install(
        self,
        state_descriptor: int,
        previous: DirectionLedger | None,
        previous_entry: _PathEntry | None,
        installed: _PathEntry,
        installation_temporary: _OwnedTemporary,
    ) -> None:
        if previous is None:
            self._remove_initial_install(
                state_descriptor,
                installed,
                installation_temporary,
            )
        else:
            if previous_entry is None:
                raise DirectionConflictError("previous Direction entry is unavailable for rollback")
            current = self._regular_entry(state_descriptor)
            if current != installed:
                raise DirectionConflictError(
                    "installed Direction changed before invalid promotion could roll back"
                )
            rollback_content = deterministic_document_bytes(previous)
            rollback_temporary = self._write_temporary(
                state_descriptor,
                rollback_content,
                mode=previous_entry.mode,
            )
            preserve_temporary = False
            cleanup_entry = rollback_temporary.entry
            try:
                try:
                    displaced_matches = self._exchange_if_current(
                        state_descriptor,
                        rollback_temporary,
                        "directions.json",
                        expected_displaced=current,
                    )
                    if not displaced_matches:
                        raise DirectionConflictError(
                            "installed Direction changed during invalid promotion rollback"
                        )
                    cleanup_entry = current
                except BaseException:
                    preserve_temporary = True
                    raise
            finally:
                if not preserve_temporary:
                    self._discard_if_exact(
                        state_descriptor,
                        rollback_temporary.name,
                        cleanup_entry,
                    )
        os.fsync(state_descriptor)

    def save(
        self,
        previous: DirectionLedger | None,
        ledger: DirectionLedger,
        expected_revision: TargetRevision,
    ) -> None:
        final_content = deterministic_document_bytes(ledger)
        with self._state_directory(create=True) as (
            parent_descriptor,
            root_descriptor,
            state_descriptor,
        ):
            self._reject_legacy_temporary_symlink(state_descriptor)
            previous_entry: _PathEntry | None = None
            if previous is None:
                try:
                    metadata = os.stat(
                        "directions.json",
                        dir_fd=state_descriptor,
                        follow_symlinks=False,
                    )
                except FileNotFoundError:
                    pass
                else:
                    if stat.S_ISLNK(metadata.st_mode):
                        raise ValidationError("Direction ledger must not be a symlink")
                    raise DirectionConflictError(
                        "approved Direction history appeared during promotion"
                    )
            else:
                previous_entry = self._regular_entry(state_descriptor)
                if previous_entry.content != deterministic_document_bytes(previous):
                    raise DirectionConflictError(
                        "approved Direction history changed during promotion"
                    )

            temporary = self._write_temporary(state_descriptor, final_content)
            installed = False
            preserve_temporary = False
            temporary_removed = False
            cleanup_entry = temporary.entry
            try:
                self._assert_sink_attached(
                    parent_descriptor,
                    root_descriptor,
                    state_descriptor,
                )
                before_install = _inspect_direction_revision(self.repository, self)
                self._assert_sink_attached(
                    parent_descriptor,
                    root_descriptor,
                    state_descriptor,
                )
                temporary_path = f".second-mate/{temporary.name}"
                if not _same_revision_except(
                    before_install,
                    expected_revision,
                    frozenset({temporary_path}),
                ):
                    raise DirectionConflictError(
                        "revision drift invalidated Direction promotion before install"
                    )
                if previous is None:
                    try:
                        os.link(
                            temporary.name,
                            "directions.json",
                            src_dir_fd=state_descriptor,
                            dst_dir_fd=state_descriptor,
                            follow_symlinks=False,
                        )
                    except FileExistsError as error:
                        raise DirectionConflictError(
                            "approved Direction history appeared during promotion"
                        ) from error
                    installed = True
                    try:
                        final_entry = self._path_entry(state_descriptor, "directions.json")
                        current_temporary = self._path_entry(
                            state_descriptor,
                            temporary.name,
                        )
                    except Exception as error:
                        preserve_temporary = True
                        raise _ExchangeRecoveryError(
                            "initial Direction temporary identity was retained after link"
                        ) from error
                    if final_entry != temporary.entry or current_temporary != temporary.entry:
                        if current_temporary != temporary.entry:
                            preserve_temporary = True
                        raise _ExchangeRecoveryError(
                            "initial Direction temporary changed across link and was retained"
                        )
                else:
                    if previous_entry is None:
                        raise DirectionConflictError(
                            "previous Direction entry is unavailable for exchange"
                        )
                    try:
                        displaced_matches = self._exchange_if_current(
                            state_descriptor,
                            temporary,
                            "directions.json",
                            expected_displaced=previous_entry,
                        )
                    except _ExchangeRecoveryError:
                        preserve_temporary = True
                        raise
                    if not displaced_matches:
                        raise DirectionConflictError(
                            "Direction history drifted during atomic promotion exchange"
                        )
                    installed = True
                    cleanup_entry = previous_entry
                os.fsync(state_descriptor)
                self._assert_sink_attached(
                    parent_descriptor,
                    root_descriptor,
                    state_descriptor,
                )
                after_install = _inspect_direction_revision(self.repository, self)
                self._assert_sink_attached(
                    parent_descriptor,
                    root_descriptor,
                    state_descriptor,
                )
                if not _matches_installed_ledger(
                    after_install,
                    expected_revision,
                    final_content,
                    temporary_path,
                    cleanup_entry,
                ):
                    raise DirectionConflictError(
                        "revision drift invalidated Direction promotion during install"
                    )
                try:
                    self._discard_if_exact(
                        state_descriptor,
                        temporary.name,
                        cleanup_entry,
                    )
                except _ExchangeRecoveryError:
                    preserve_temporary = True
                    raise
                temporary_removed = True
                self._assert_sink_attached(
                    parent_descriptor,
                    root_descriptor,
                    state_descriptor,
                )
                final_revision = _inspect_direction_revision(self.repository, self)
                self._assert_sink_attached(
                    parent_descriptor,
                    root_descriptor,
                    state_descriptor,
                )
                if not _matches_installed_ledger(
                    final_revision,
                    expected_revision,
                    final_content,
                ):
                    raise DirectionConflictError(
                        "revision drift invalidated Direction promotion during finalization"
                    )
            except BaseException:
                if installed:
                    try:
                        self._rollback_install(
                            state_descriptor,
                            previous,
                            previous_entry,
                            temporary.entry,
                            temporary,
                        )
                    except Exception as rollback_error:
                        if previous is not None or isinstance(
                            rollback_error,
                            _ExchangeRecoveryError,
                        ):
                            preserve_temporary = True
                        raise DirectionConflictError(
                            "Direction promotion was invalidated and prior history "
                            "could not be restored"
                        ) from rollback_error
                raise
            finally:
                if not preserve_temporary and not temporary_removed:
                    self._discard_if_exact(
                        state_descriptor,
                        temporary.name,
                        cleanup_entry,
                    )


@contextmanager
def _direction_lock(repository: Path) -> Iterator[None]:
    try:
        with mutation_lock(repository):
            yield
    except MutationLockBusyError as error:
        raise DirectionConflictError(
            "the repository mutation boundary is held by an active operation"
        ) from error


def prepare_direction(
    repository: Path,
    summary: str,
    *,
    direction_id: str,
    change_note: str | None,
) -> DirectionCandidateEnvelope:
    """Freeze an editable summary into a read-only, approval-ready candidate."""
    root = repository_root(repository)
    if repository_path_is_ignored(root, _ALLOWED_PATHS[0]):
        raise ValidationError("approved Direction project state must not be ignored by Git")
    if not summary.strip():
        raise ValidationError("Direction Summary must be non-empty")
    store = _DirectionLedgerStore(root)
    store.reject_missing_recorded_history()
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
    revision = _inspect_direction_revision(root, store)
    return DirectionCandidateEnvelope(
        candidate=candidate,
        digest=digest_json(candidate.to_json()),
        promotion_basis=PromotionBasis(
            target_root=os.fspath(root),
            target_head=revision.head,
            target_fingerprint=revision.fingerprint,
        ),
    )


def promote_direction(
    repository: Path,
    candidate_data: object,
    approval_data: object | None,
    promotion_grant_data: object | None,
) -> ApprovedDirectionVersion:
    """Persist only a separately and exactly approved Direction candidate."""
    root = repository_root(repository)
    candidate = _candidate_envelope_from_json(candidate_data)
    approval = _approval_from_json(approval_data)
    promotion_grant = _promotion_grant_from_json(promotion_grant_data)
    if approval.direction_id != candidate.candidate.id:
        raise ValidationError("Direction approval identifies a different candidate")
    if approval.candidate_digest != candidate.digest:
        raise ValidationError("Direction approval digest does not match the exact candidate")
    expected_grant: dict[str, object] = {
        "candidate_digest": candidate.digest,
        "target_root": candidate.promotion_basis.target_root,
        "target_head": candidate.promotion_basis.target_head,
        "target_fingerprint": candidate.promotion_basis.target_fingerprint,
    }
    for field, expected_value in expected_grant.items():
        if getattr(promotion_grant, field) != expected_value:
            raise ValidationError(f"promotion grant {field} does not match the prepared basis")
    if os.fspath(root) != candidate.promotion_basis.target_root:
        raise ValidationError("Direction candidate was prepared for a different target")
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
        store.reject_missing_recorded_history()
        if store.has_open_run():
            raise DirectionConflictError("an open packet run must close before Direction promotion")
        if repository_path_is_ignored(root, _ALLOWED_PATHS[0]):
            raise ValidationError("approved Direction project state must not be ignored by Git")
        current_revision = _inspect_direction_revision(root, store)
        if (
            current_revision.head != candidate.promotion_basis.target_head
            or current_revision.fingerprint != candidate.promotion_basis.target_fingerprint
        ):
            raise DirectionConflictError("revision drift invalidated Direction promotion authority")
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
            if any(item.promotion_grant.id == promotion_grant.id for item in previous.versions):
                raise DirectionConflictError("an explicit promotion grant id cannot be reused")
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
            promotion_grant=promotion_grant,
            supersedes=candidate.candidate.supersedes,
            change_note=candidate.candidate.change_note,
        )
        ledger = DirectionLedger(
            versions=(version,) if previous is None else (*previous.versions, version)
        )
        store.save(previous, ledger, current_revision)
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
