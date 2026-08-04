"""Deterministic repository-local state and recoverable close persistence."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import secrets
import stat
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from second_mate.domain import JsonObject

_CLOSE_JOURNAL_SCHEMA_VERSION = 2
_INTENT_TOKEN_HEX_LENGTH = 32
_AT_FDCWD = -100
_RENAME_EXCHANGE = 2


class JsonDocument(Protocol):
    def to_json(self) -> JsonObject:
        """Return a complete JSON representation."""


class StateRecoveryError(RuntimeError):
    """A close journal cannot be reconciled with the current durable state."""


class StrictJsonError(ValueError):
    """A JSON object contains an ambiguous duplicate field name."""


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise StrictJsonError(f"duplicate JSON object field: {key}")
        document[key] = value
    return document


def strict_json_loads(document: str | bytes) -> object:
    """Decode JSON while rejecting duplicate fields at every nesting level."""
    return json.loads(document, object_pairs_hook=_strict_object)


def deterministic_json_bytes(value: JsonObject) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def deterministic_document_bytes(document: JsonDocument) -> bytes:
    return deterministic_json_bytes(document.to_json())


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _is_lower_hex(value: str, length: int) -> bool:
    return len(value) == length and all(character in "0123456789abcdef" for character in value)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _read_unaliased_file(path: Path, label: str) -> bytes:
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
        if (metadata.st_dev, metadata.st_ino) != (
            entry_after.st_dev,
            entry_after.st_ino,
        ):
            raise OSError(f"{label} identity changed while reading")
        return content
    except OSError as error:
        raise StateRecoveryError(f"cannot safely read {label}: {error}") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


class AtomicWriter(Protocol):
    """Narrow crash-boundary port used by normal saves and close recovery tests."""

    def write(self, path: Path, content: bytes, *, intent_directory: Path) -> None:
        """Atomically replace path with content."""


@dataclass(frozen=True, slots=True)
class AtomicWriteIntent:
    """One durable, Git-private claim over a randomized target scratch path."""

    content_sha256: str
    content: bytes
    token: str
    marker: Path
    scratch: Path
    staging: Path | None = None


def _intent_target_key(path: Path) -> str:
    return _digest(os.fsencode(path.absolute()))


def _intent_marker_name(path: Path, content_sha256: str, token: str) -> str:
    return f"intent.{_intent_target_key(path)}.{content_sha256}.{token}"


def _scratch_path(path: Path, content_sha256: str, token: str) -> Path:
    return path.with_name(f"{path.name}.next.{content_sha256}.{token}")


def _staging_marker_path(
    intent_directory: Path,
    path: Path,
    content_sha256: str,
    token: str,
) -> Path:
    return intent_directory / f"staging.{_intent_target_key(path)}.{content_sha256}.{token}"


def _validate_private_directory(path: Path, *, create: bool) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        if not create:
            return False
        try:
            parent_metadata = path.parent.lstat()
        except OSError as error:
            raise StateRecoveryError(
                f"cannot inspect atomic intent parent directory: {error}"
            ) from error
        if (
            not stat.S_ISDIR(parent_metadata.st_mode)
            or path.parent.resolve(strict=True) != path.parent
        ):
            raise StateRecoveryError(
                "atomic intent parent directory must be unaliased and real"
            ) from None
        try:
            os.mkdir(path, 0o700)
        except OSError as error:
            raise StateRecoveryError(f"cannot create atomic intent directory: {error}") from error
        metadata = path.lstat()
    except OSError as error:
        raise StateRecoveryError(f"cannot inspect atomic intent directory: {error}") from error
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) & 0o077 != 0
        or path.resolve(strict=True) != path
    ):
        raise StateRecoveryError(
            "atomic intent directory must be owner-private, unaliased, and real"
        )
    if create:
        _fsync_directory(path.parent)
    return True


def _read_intent_marker(marker: Path) -> bytes:
    try:
        metadata = marker.lstat()
    except OSError as error:
        raise StateRecoveryError(f"cannot inspect atomic intent marker: {error}") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
    ):
        raise StateRecoveryError(
            "atomic intent marker must be one owner-private unaliased regular file"
        )
    return _read_unaliased_file(marker, "atomic intent marker")


def _read_linked_intent_marker(marker: Path, staging: Path) -> bytes:
    descriptor: int | None = None
    try:
        descriptor = os.open(marker, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        metadata = os.fstat(descriptor)
        marker_entry = marker.lstat()
        staging_entry = staging.lstat()
        identity = (metadata.st_dev, metadata.st_ino)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 2
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or identity != (marker_entry.st_dev, marker_entry.st_ino)
            or identity != (staging_entry.st_dev, staging_entry.st_ino)
            or staging_entry.st_nlink != 2
        ):
            raise OSError("unsafe linked atomic intent marker identity")
        with os.fdopen(descriptor, "rb", closefd=True) as stream:
            descriptor = None
            content = stream.read()
        marker_after = marker.lstat()
        staging_after = staging.lstat()
        if identity != (marker_after.st_dev, marker_after.st_ino) or identity != (
            staging_after.st_dev,
            staging_after.st_ino,
        ):
            raise OSError("linked atomic intent marker identity changed while reading")
        return content
    except OSError as error:
        raise StateRecoveryError(
            f"cannot safely read linked atomic intent marker: {error}"
        ) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _scan_atomic_intents(path: Path, intent_directory: Path) -> tuple[AtomicWriteIntent, ...]:
    if not _validate_private_directory(intent_directory, create=False):
        return ()
    target_key = _intent_target_key(path)
    prefix = f"intent.{target_key}."
    intents: list[AtomicWriteIntent] = []
    try:
        entries = tuple(intent_directory.iterdir())
    except OSError as error:
        raise StateRecoveryError(f"cannot inspect atomic intent markers: {error}") from error
    for marker in entries:
        if not marker.name.startswith(prefix):
            continue
        parts = marker.name.split(".")
        if (
            len(parts) != 4
            or parts[0] != "intent"
            or parts[1] != target_key
            or not _is_lower_hex(parts[2], 64)
            or not _is_lower_hex(parts[3], _INTENT_TOKEN_HEX_LENGTH)
        ):
            raise StateRecoveryError("atomic intent marker name is invalid")
        scratch = _scratch_path(path, parts[2], parts[3])
        staging = _staging_marker_path(intent_directory, path, parts[2], parts[3])
        try:
            marker_metadata = marker.lstat()
        except OSError as error:
            raise StateRecoveryError(f"cannot inspect atomic intent marker: {error}") from error
        if marker_metadata.st_nlink == 1:
            marker_content = _read_intent_marker(marker)
            interrupted_staging = None
        elif marker_metadata.st_nlink == 2:
            marker_content = _read_linked_intent_marker(marker, staging)
            interrupted_staging = staging
        else:
            raise StateRecoveryError("atomic intent marker link count is invalid")
        if _digest(marker_content) != parts[2]:
            raise StateRecoveryError(
                "atomic intent marker content does not match its declared digest"
            )
        intents.append(
            AtomicWriteIntent(
                content_sha256=parts[2],
                content=marker_content,
                token=parts[3],
                marker=marker,
                scratch=scratch,
                staging=interrupted_staging,
            )
        )
    return tuple(intents)


def _read_atomic_intents(path: Path, intent_directory: Path) -> tuple[AtomicWriteIntent, ...]:
    return _scan_atomic_intents(path, intent_directory)


def _read_private_scratch(path: Path) -> bytes:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise StateRecoveryError(f"cannot inspect atomic scratch file: {error}") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
    ):
        raise StateRecoveryError(
            "atomic scratch intent must be one owner-private unaliased regular file"
        )
    return _read_unaliased_file(path, "atomic scratch file")


def _create_atomic_intent(path: Path, content: bytes, intent_directory: Path) -> AtomicWriteIntent:
    if not _validate_private_directory(intent_directory, create=False):
        raise StateRecoveryError("atomic intent directory disappeared before marker creation")
    content_sha256 = _digest(content)
    for _ in range(8):
        token = secrets.token_hex(_INTENT_TOKEN_HEX_LENGTH // 2)
        marker = intent_directory / _intent_marker_name(path, content_sha256, token)
        staging = _staging_marker_path(
            intent_directory,
            path,
            content_sha256,
            token,
        )
        try:
            descriptor = os.open(
                staging,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                0o600,
            )
        except FileExistsError:
            continue
        except OSError as error:
            raise StateRecoveryError(f"cannot create atomic intent marker: {error}") from error
        try:
            os.fchmod(descriptor, 0o600)
            remaining = memoryview(content)
            while remaining:
                written = os.write(descriptor, remaining)
                if written == 0:
                    raise OSError("atomic intent marker write made no progress")
                remaining = remaining[written:]
            os.fsync(descriptor)
            metadata = os.fstat(descriptor)
        except OSError as error:
            os.close(descriptor)
            raise StateRecoveryError(f"cannot secure atomic intent marker: {error}") from error
        except BaseException:
            with suppress(OSError):
                os.close(descriptor)
            raise
        os.close(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise StateRecoveryError("atomic intent staging marker identity is unsafe")
        if _read_intent_marker(staging) != content:
            raise StateRecoveryError("atomic intent staging content changed while preparing")
        try:
            os.link(staging, marker, follow_symlinks=False)
        except FileExistsError:
            staging.unlink()
            _fsync_directory(intent_directory)
            continue
        except OSError as error:
            raise StateRecoveryError(f"cannot publish atomic intent marker: {error}") from error
        _fsync_directory(intent_directory)
        try:
            staging.unlink()
        except OSError as error:
            raise StateRecoveryError(
                f"cannot complete atomic intent marker publication: {error}"
            ) from error
        _fsync_directory(intent_directory)
        if _read_intent_marker(marker) != content:
            raise StateRecoveryError("atomic intent marker content changed while publishing")
        return AtomicWriteIntent(
            content_sha256=content_sha256,
            content=content,
            token=token,
            marker=marker,
            scratch=_scratch_path(path, content_sha256, token),
        )
    raise StateRecoveryError("cannot reserve a unique atomic intent marker")


def _delete_atomic_intent(intent: AtomicWriteIntent) -> None:
    if (
        _read_intent_marker(intent.marker) != intent.content
        or _digest(intent.content) != intent.content_sha256
    ):
        raise StateRecoveryError("atomic intent marker content changed before retirement")
    try:
        intent.marker.unlink()
    except OSError as error:
        raise StateRecoveryError(f"cannot retire atomic intent marker: {error}") from error
    _fsync_directory(intent.marker.parent)


def _finish_atomic_marker_publication(intent: AtomicWriteIntent) -> None:
    if intent.staging is None:
        return
    if _read_linked_intent_marker(intent.marker, intent.staging) != intent.content:
        raise StateRecoveryError("linked atomic intent marker content changed during recovery")
    try:
        intent.staging.unlink()
    except OSError as error:
        raise StateRecoveryError(
            f"cannot finish interrupted atomic intent publication: {error}"
        ) from error
    _fsync_directory(intent.marker.parent)
    if _read_intent_marker(intent.marker) != intent.content:
        raise StateRecoveryError("atomic intent marker changed after publication recovery")


def _redurable_atomic_intent(intent: AtomicWriteIntent) -> None:
    descriptor: int | None = None
    try:
        descriptor = os.open(
            intent.marker,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        metadata = os.fstat(descriptor)
        entry = intent.marker.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or (metadata.st_dev, metadata.st_ino) != (entry.st_dev, entry.st_ino)
        ):
            raise OSError("unsafe atomic intent marker identity")
        os.fsync(descriptor)
    except OSError as error:
        raise StateRecoveryError(
            f"cannot restore atomic intent marker durability: {error}"
        ) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if _read_intent_marker(intent.marker) != intent.content:
        raise StateRecoveryError("atomic intent marker changed while restoring durability")
    _fsync_directory(intent.marker.parent)


def recovery_intent_paths(
    path: Path, content: bytes, *, intent_directory: Path
) -> tuple[Path, ...]:
    """Return only durably marked target scratches for this exact intended content."""
    digest = _digest(content)
    matching = tuple(
        intent.scratch
        for intent in _read_atomic_intents(path.absolute(), intent_directory.absolute())
        if intent.content_sha256 == digest and intent.content == content
    )
    if len(matching) > 1:
        raise StateRecoveryError("multiple atomic intents claim the same target content")
    return matching


def prepare_atomic_write_intent(
    path: Path, content: bytes, *, intent_directory: Path
) -> AtomicWriteIntent:
    """Validate reserved paths and durably claim one randomized scratch path."""
    path = path.absolute()
    intent_directory = intent_directory.absolute()
    try:
        target_container_metadata = path.parent.parent.lstat()
    except OSError as error:
        raise StateRecoveryError(f"cannot inspect atomic target container: {error}") from error
    if (
        not stat.S_ISDIR(target_container_metadata.st_mode)
        or path.parent.parent.resolve(strict=True) != path.parent.parent
    ):
        raise StateRecoveryError("atomic target container must be unaliased and real")
    try:
        os.mkdir(path.parent, 0o700)
    except FileExistsError:
        pass
    except OSError as error:
        raise StateRecoveryError(f"cannot create atomic target directory: {error}") from error
    try:
        parent_metadata = path.parent.lstat()
    except OSError as error:
        raise StateRecoveryError(f"cannot inspect atomic target directory: {error}") from error
    if not stat.S_ISDIR(parent_metadata.st_mode) or path.parent.resolve(strict=True) != path.parent:
        raise StateRecoveryError("atomic target directory must be unaliased and real")
    _fsync_directory(path.parent.parent)
    legacy_temporary = path.with_name(f"{path.name}.next")
    try:
        legacy_temporary.lstat()
    except FileNotFoundError:
        pass
    except OSError as error:
        raise StateRecoveryError(f"cannot inspect atomic scratch file: {error}") from error
    else:
        raise StateRecoveryError("a legacy atomic scratch collision blocks the write")

    _validate_private_directory(intent_directory, create=True)
    intents = _scan_atomic_intents(path, intent_directory)
    for intent in intents:
        _finish_atomic_marker_publication(intent)
        _redurable_atomic_intent(intent)
    by_scratch = {intent.scratch: intent for intent in intents}
    scratch_prefix = f"{path.name}.next."
    try:
        scratch_entries = tuple(
            entry for entry in path.parent.iterdir() if entry.name.startswith(scratch_prefix)
        )
    except OSError as error:
        raise StateRecoveryError(f"cannot inspect atomic write intents: {error}") from error
    for scratch in scratch_entries:
        if scratch not in by_scratch:
            raise StateRecoveryError("atomic write intent has no durable ownership marker")
        _read_private_scratch(scratch)

    content_sha256 = _digest(content)
    matching = tuple(intent for intent in intents if intent.content_sha256 == content_sha256)
    if len(matching) > 1:
        raise StateRecoveryError("multiple atomic intents claim the same target content")
    if matching and matching[0].content != content:
        raise StateRecoveryError("atomic intent marker content does not match the intended write")
    desired = matching[0] if matching else _create_atomic_intent(path, content, intent_directory)
    for prior in intents:
        if prior == desired:
            continue
        if prior.scratch in scratch_entries:
            prior_scratch = _read_private_scratch(prior.scratch)
            if not prior.content.startswith(prior_scratch):
                raise StateRecoveryError(
                    "prior atomic scratch content does not match its durable ownership marker"
                )
            try:
                prior.scratch.unlink()
            except OSError as error:
                raise StateRecoveryError(
                    f"cannot retire prior atomic write scratch: {error}"
                ) from error
            _fsync_directory(path.parent)
        _delete_atomic_intent(prior)
    return desired


def pending_atomic_exchange(
    path: Path,
    *,
    intent_directory: Path,
) -> tuple[bytes, bytes] | None:
    """Return the exact displaced and installed sides of one interrupted exchange."""
    path = path.absolute()
    intent_directory = intent_directory.absolute()
    try:
        path.lstat()
    except FileNotFoundError:
        return None
    except OSError as error:
        raise StateRecoveryError(f"cannot inspect exchanged atomic target: {error}") from error
    installed = _read_unaliased_file(path, "exchanged atomic target")
    matching: list[AtomicWriteIntent] = []
    for intent in _read_atomic_intents(path, intent_directory):
        try:
            intent.scratch.lstat()
        except FileNotFoundError:
            continue
        except OSError as error:
            raise StateRecoveryError(f"cannot inspect exchanged prior target: {error}") from error
        if intent.content == installed:
            matching.append(intent)
    if not matching:
        return None
    if len(matching) != 1:
        raise StateRecoveryError("multiple atomic intents claim the installed exchange")
    displaced = _read_unaliased_file(matching[0].scratch, "exchanged prior target")
    return displaced, installed


class PosixAtomicWriter:
    """Durably marked same-directory replacement for the verified FS-01 environment."""

    @staticmethod
    def _write_scratch(
        path: Path,
        content: bytes,
        *,
        intent_directory: Path,
    ) -> tuple[AtomicWriteIntent, os.stat_result]:
        intent = prepare_atomic_write_intent(
            path,
            content,
            intent_directory=intent_directory,
        )
        temporary = intent.scratch
        try:
            declared = temporary.lstat()
        except FileNotFoundError:
            declared = None
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
        except OSError as error:
            raise StateRecoveryError(f"cannot inspect atomic scratch file: {error}") from error
        else:
            assert declared is not None
            existing = _read_private_scratch(temporary)
            if not content.startswith(existing):
                raise StateRecoveryError(
                    "atomic scratch content does not match its durable ownership marker"
                )
            flags = os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC
        try:
            descriptor = os.open(
                temporary,
                flags,
                0o600,
            )
        except OSError as error:
            raise StateRecoveryError(f"cannot safely open atomic scratch file: {error}") from error
        try:
            os.fchmod(descriptor, 0o600)
            metadata = os.fstat(descriptor)
        except OSError as error:
            os.close(descriptor)
            raise StateRecoveryError(f"cannot secure atomic scratch file: {error}") from error
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_uid != os.geteuid()
            or (
                declared is not None
                and (metadata.st_dev, metadata.st_ino) != (declared.st_dev, declared.st_ino)
            )
        ):
            os.close(descriptor)
            raise StateRecoveryError("atomic scratch path must be one unaliased regular file")
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                os.ftruncate(stream.fileno(), 0)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            with suppress(OSError):
                os.close(descriptor)
            raise
        try:
            entry = temporary.lstat()
        except OSError as error:
            raise StateRecoveryError(f"cannot verify atomic scratch file: {error}") from error
        if (metadata.st_dev, metadata.st_ino) != (entry.st_dev, entry.st_ino):
            raise StateRecoveryError("atomic scratch identity changed before replacement")
        if _read_intent_marker(intent.marker) != content:
            raise StateRecoveryError("atomic intent marker changed before replacement")
        return intent, metadata

    @staticmethod
    def _retire_scratch(
        intent: AtomicWriteIntent,
        metadata: os.stat_result,
        content: bytes,
    ) -> None:
        try:
            entry = intent.scratch.lstat()
        except OSError as error:
            raise StateRecoveryError(f"cannot retire atomic scratch file: {error}") from error
        if (
            not stat.S_ISREG(entry.st_mode)
            or entry.st_uid != os.geteuid()
            or stat.S_IMODE(entry.st_mode) != 0o600
            or entry.st_nlink not in {1, 2}
            or (metadata.st_dev, metadata.st_ino) != (entry.st_dev, entry.st_ino)
            or _read_intent_marker(intent.marker) != content
        ):
            raise StateRecoveryError("atomic scratch identity changed before retirement")
        if entry.st_nlink == 1 and _read_private_scratch(intent.scratch) != content:
            raise StateRecoveryError("atomic scratch content changed before retirement")
        try:
            intent.scratch.unlink()
        except OSError as error:
            raise StateRecoveryError(f"cannot retire atomic scratch file: {error}") from error
        _fsync_directory(intent.scratch.parent)
        _delete_atomic_intent(intent)

    def create(self, path: Path, content: bytes, *, intent_directory: Path) -> None:
        """Atomically install new content without replacing any existing entry."""
        intent, metadata = self._write_scratch(
            path,
            content,
            intent_directory=intent_directory,
        )
        try:
            os.link(intent.scratch, path, follow_symlinks=False)
        except FileExistsError as error:
            try:
                final_entry = path.lstat()
                scratch_entry = intent.scratch.lstat()
            except OSError as inspect_error:
                raise StateRecoveryError(
                    f"cannot inspect colliding atomic target: {inspect_error}"
                ) from inspect_error
            same_installed_inode = stat.S_ISREG(final_entry.st_mode) and (
                final_entry.st_dev,
                final_entry.st_ino,
            ) == (scratch_entry.st_dev, scratch_entry.st_ino) == (metadata.st_dev, metadata.st_ino)
            if not same_installed_inode:
                self._retire_scratch(intent, metadata, content)
                raise StateRecoveryError("atomic target already exists") from error
        except OSError as error:
            raise StateRecoveryError(f"cannot install new atomic target: {error}") from error
        _fsync_directory(path.parent)
        self._retire_scratch(intent, metadata, content)

    @staticmethod
    def _exchange_paths(left: Path, right: Path) -> None:
        library = ctypes.CDLL(None, use_errno=True)
        try:
            renameat2 = library.renameat2
        except AttributeError as error:
            raise StateRecoveryError(
                "atomic compare-and-exchange is unavailable on this platform"
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
                _AT_FDCWD,
                os.fsencode(left),
                _AT_FDCWD,
                os.fsencode(right),
                _RENAME_EXCHANGE,
            )
            != 0
        ):
            error_number = ctypes.get_errno()
            raise OSError(error_number, os.strerror(error_number))

    @staticmethod
    def _recover_completed_exchange(
        path: Path,
        expected: bytes,
        content: bytes,
        *,
        intent_directory: Path,
    ) -> bool:
        matching = tuple(
            intent
            for intent in _read_atomic_intents(path.absolute(), intent_directory.absolute())
            if intent.content_sha256 == _digest(content) and intent.content == content
        )
        if not matching:
            return False
        if len(matching) != 1:
            raise StateRecoveryError("multiple atomic intents claim the exchanged target")
        intent = matching[0]
        try:
            path.lstat()
            intent.scratch.lstat()
        except FileNotFoundError:
            return False
        except OSError as error:
            raise StateRecoveryError(f"cannot inspect exchanged atomic target: {error}") from error
        displaced = _read_unaliased_file(intent.scratch, "exchanged prior target")
        installed = _read_unaliased_file(path, "exchanged atomic target")
        if displaced != expected or installed != content:
            raise StateRecoveryError("interrupted atomic exchange does not match either exact side")
        try:
            intent.scratch.unlink()
        except OSError as error:
            raise StateRecoveryError(f"cannot retire exchanged prior target: {error}") from error
        _fsync_directory(path.parent)
        _delete_atomic_intent(intent)
        return True

    def exchange(
        self,
        path: Path,
        expected: bytes,
        content: bytes,
        *,
        intent_directory: Path,
    ) -> None:
        """Atomically replace only the exact expected content, restoring any race winner."""
        path = path.absolute()
        intent_directory = intent_directory.absolute()
        if self._recover_completed_exchange(
            path,
            expected,
            content,
            intent_directory=intent_directory,
        ):
            return
        intent, metadata = self._write_scratch(
            path,
            content,
            intent_directory=intent_directory,
        )
        try:
            self._exchange_paths(intent.scratch, path)
        except OSError as error:
            self._retire_scratch(intent, metadata, content)
            raise StateRecoveryError(f"cannot exchange atomic target: {error}") from error
        _fsync_directory(path.parent)
        try:
            displaced = _read_unaliased_file(intent.scratch, "exchanged prior target")
            installed = _read_unaliased_file(path, "exchanged atomic target")
        except StateRecoveryError as error:
            try:
                self._exchange_paths(intent.scratch, path)
                _fsync_directory(path.parent)
            except OSError as rollback_error:
                raise StateRecoveryError(
                    "atomic exchange inspection failed and prior target could not be restored"
                ) from rollback_error
            self._retire_scratch(intent, metadata, content)
            raise error
        if displaced != expected or installed != content:
            try:
                self._exchange_paths(intent.scratch, path)
                _fsync_directory(path.parent)
            except OSError as error:
                raise StateRecoveryError(
                    "atomic target changed and could not be restored after exchange"
                ) from error
            if _read_unaliased_file(path, "restored atomic target") != displaced:
                raise StateRecoveryError("atomic target restoration produced different content")
            self._retire_scratch(intent, metadata, content)
            raise StateRecoveryError("atomic target changed before compare-and-exchange")
        try:
            intent.scratch.unlink()
        except OSError as error:
            raise StateRecoveryError(f"cannot retire exchanged prior target: {error}") from error
        _fsync_directory(path.parent)
        _delete_atomic_intent(intent)

    def write(self, path: Path, content: bytes, *, intent_directory: Path) -> None:
        intent, _ = self._write_scratch(
            path,
            content,
            intent_directory=intent_directory,
        )
        temporary = intent.scratch
        os.replace(temporary, path)
        _fsync_directory(path.parent)
        _delete_atomic_intent(intent)


RecoveryValidator = Callable[[object, object], None]


class FileStateStore:
    """Persist one state document and recover its clean-close transaction."""

    def __init__(
        self,
        path: Path,
        *,
        intent_directory: Path,
        writer: AtomicWriter | None = None,
        recovery_validator: RecoveryValidator | None = None,
    ) -> None:
        self.path = path.absolute()
        self.pending_path = self.path.with_name(f"{self.path.name}.pending")
        self.intent_directory = intent_directory.absolute()
        self.writer = PosixAtomicWriter() if writer is None else writer
        self.recovery_validator = recovery_validator

    def _validate_parent(self) -> None:
        try:
            metadata = self.path.parent.lstat()
        except FileNotFoundError:
            return
        except OSError as error:
            raise StateRecoveryError(f"cannot inspect state directory: {error}") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise StateRecoveryError("state directory must not be a symlink")
        if not stat.S_ISDIR(metadata.st_mode):
            raise StateRecoveryError("state parent must be a directory")

    def _read_unaliased(self, path: Path, label: str) -> bytes:
        return _read_unaliased_file(path, label)

    def _entry_exists(self, path: Path, label: str) -> bool:
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            return False
        except OSError as error:
            raise StateRecoveryError(f"cannot inspect {label}: {error}") from error
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or path.resolve(strict=True) != path
        ):
            raise StateRecoveryError(f"{label} must be one unaliased regular file")
        return True

    def exists(self) -> bool:
        self._validate_parent()
        state_exists = self._entry_exists(self.path, "durable state")
        pending_exists = self._entry_exists(self.pending_path, "close recovery journal")
        return state_exists or pending_exists

    def _finish_pending_close(self) -> None:
        self._validate_parent()
        if not self._entry_exists(self.pending_path, "close recovery journal"):
            return
        try:
            raw = strict_json_loads(
                self._read_unaliased(self.pending_path, "close recovery journal")
            )
        except (UnicodeError, json.JSONDecodeError, StrictJsonError) as error:
            raise StateRecoveryError(f"cannot read close recovery journal: {error}") from error
        if not isinstance(raw, dict) or not all(isinstance(key, str) for key in raw):
            raise StateRecoveryError("close recovery journal must be an object")
        journal = cast(dict[str, object], raw)
        if (
            set(journal)
            != {
                "base_document",
                "base_sha256",
                "final_document",
                "final_sha256",
                "schema_version",
            }
            or type(journal["schema_version"]) is not int
            or journal["schema_version"] != _CLOSE_JOURNAL_SCHEMA_VERSION
        ):
            raise StateRecoveryError("close recovery journal schema is invalid")
        base_raw = journal["base_document"]
        final_raw = journal["final_document"]
        if (
            not isinstance(base_raw, dict)
            or not all(isinstance(key, str) for key in base_raw)
            or not isinstance(final_raw, dict)
            or not all(isinstance(key, str) for key in final_raw)
        ):
            raise StateRecoveryError("close recovery documents are invalid")
        base_document = cast(JsonObject, base_raw)
        final_document = cast(JsonObject, final_raw)
        base_content = deterministic_json_bytes(base_document)
        final_content = deterministic_json_bytes(final_document)
        base_sha = journal["base_sha256"]
        final_sha = journal["final_sha256"]
        if not isinstance(base_sha, str) or not isinstance(final_sha, str):
            raise StateRecoveryError("close recovery hashes are invalid")
        if _digest(base_content) != base_sha or _digest(final_content) != final_sha:
            raise StateRecoveryError("close recovery document hash is invalid")
        if self.recovery_validator is None:
            raise StateRecoveryError("close recovery requires a semantic transition validator")
        try:
            self.recovery_validator(base_document, final_document)
        except Exception as error:
            raise StateRecoveryError(f"close recovery transition is invalid: {error}") from error
        current = self._read_unaliased(self.path, "durable state during recovery")
        current_sha = _digest(current)
        if current_sha == base_sha:
            self.writer.write(
                self.path,
                final_content,
                intent_directory=self.intent_directory,
            )
        elif current_sha != final_sha:
            raise StateRecoveryError("durable state diverged from both sides of close transaction")
        self._entry_exists(self.pending_path, "close recovery journal")
        self.pending_path.unlink()
        _fsync_directory(self.pending_path.parent)

    def read_json(self) -> object:
        self._finish_pending_close()
        try:
            return strict_json_loads(self._read_unaliased(self.path, "durable state"))
        except (UnicodeError, json.JSONDecodeError, StrictJsonError) as error:
            raise RuntimeError(f"cannot read durable state: {error}") from error

    def save(self, document: JsonDocument) -> None:
        self._validate_parent()
        if self._entry_exists(self.pending_path, "close recovery journal"):
            self._finish_pending_close()
        self.writer.write(
            self.path,
            deterministic_document_bytes(document),
            intent_directory=self.intent_directory,
        )

    def close(self, previous: JsonDocument, final: JsonDocument) -> None:
        """Write a recoverable journal before atomically installing the complete close."""
        self._validate_parent()
        base_content = deterministic_document_bytes(previous)
        final_document = final.to_json()
        final_content = deterministic_json_bytes(final_document)
        current_content = self._read_unaliased(self.path, "durable state before close")
        if current_content != base_content:
            raise StateRecoveryError("durable state changed before clean close")
        journal: JsonObject = {
            "base_document": previous.to_json(),
            "base_sha256": _digest(base_content),
            "final_document": final_document,
            "final_sha256": _digest(final_content),
            "schema_version": _CLOSE_JOURNAL_SCHEMA_VERSION,
        }
        self.writer.write(
            self.pending_path,
            deterministic_json_bytes(journal),
            intent_directory=self.intent_directory,
        )
        self.writer.write(
            self.path,
            final_content,
            intent_directory=self.intent_directory,
        )
        self.pending_path.unlink()
        _fsync_directory(self.pending_path.parent)
