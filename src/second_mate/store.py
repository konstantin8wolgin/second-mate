"""Deterministic repository-local state and recoverable close persistence."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import suppress
from pathlib import Path
from typing import Protocol, cast

from second_mate.domain import JsonObject


class JsonDocument(Protocol):
    def to_json(self) -> JsonObject:
        """Return a complete JSON representation."""


class StateRecoveryError(RuntimeError):
    """A close journal cannot be reconciled with the current durable state."""


def deterministic_json_bytes(value: JsonObject) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def deterministic_document_bytes(document: JsonDocument) -> bytes:
    return deterministic_json_bytes(document.to_json())


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class AtomicWriter(Protocol):
    """Narrow crash-boundary port used by normal saves and close recovery tests."""

    def write(self, path: Path, content: bytes) -> None:
        """Atomically replace path with content."""


class PosixAtomicWriter:
    """Same-directory write, fsync, and replace for the verified FS-01 environment."""

    def write(self, path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f"{path.name}.next")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            with suppress(OSError):
                os.close(descriptor)
            raise
        os.replace(temporary, path)
        _fsync_directory(path.parent)


class FileStateStore:
    """Persist one state document and recover its clean-close transaction."""

    def __init__(self, path: Path, *, writer: AtomicWriter | None = None) -> None:
        self.path = path
        self.pending_path = path.with_name(f"{path.name}.pending")
        self.writer = PosixAtomicWriter() if writer is None else writer

    def exists(self) -> bool:
        return self.path.exists() or self.pending_path.exists()

    def _finish_pending_close(self) -> None:
        if not self.pending_path.exists():
            return
        try:
            raw = json.loads(self.pending_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise StateRecoveryError(f"cannot read close recovery journal: {error}") from error
        if not isinstance(raw, dict) or not all(isinstance(key, str) for key in raw):
            raise StateRecoveryError("close recovery journal must be an object")
        journal = cast(dict[str, object], raw)
        if (
            set(journal)
            != {
                "base_sha256",
                "final_document",
                "final_sha256",
                "schema_version",
            }
            or journal["schema_version"] != 1
        ):
            raise StateRecoveryError("close recovery journal schema is invalid")
        final_raw = journal["final_document"]
        if not isinstance(final_raw, dict) or not all(isinstance(key, str) for key in final_raw):
            raise StateRecoveryError("close recovery final document is invalid")
        final_document = cast(JsonObject, final_raw)
        final_content = deterministic_json_bytes(final_document)
        base_sha = journal["base_sha256"]
        final_sha = journal["final_sha256"]
        if not isinstance(base_sha, str) or not isinstance(final_sha, str):
            raise StateRecoveryError("close recovery hashes are invalid")
        if _digest(final_content) != final_sha:
            raise StateRecoveryError("close recovery final hash is invalid")
        try:
            current = self.path.read_bytes()
        except OSError as error:
            raise StateRecoveryError(f"cannot read base state during recovery: {error}") from error
        current_sha = _digest(current)
        if current_sha == base_sha:
            self.writer.write(self.path, final_content)
        elif current_sha != final_sha:
            raise StateRecoveryError("durable state diverged from both sides of close transaction")
        self.pending_path.unlink()
        _fsync_directory(self.pending_path.parent)

    def read_json(self) -> object:
        self._finish_pending_close()
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise RuntimeError(f"cannot read durable state: {error}") from error

    def save(self, document: JsonDocument) -> None:
        if self.pending_path.exists():
            self._finish_pending_close()
        self.writer.write(self.path, deterministic_document_bytes(document))

    def close(self, previous: JsonDocument, final: JsonDocument) -> None:
        """Write a recoverable journal before atomically installing the complete close."""
        base_content = deterministic_document_bytes(previous)
        final_document = final.to_json()
        final_content = deterministic_json_bytes(final_document)
        try:
            current_content = self.path.read_bytes()
        except OSError as error:
            raise StateRecoveryError(f"cannot read state before close: {error}") from error
        if current_content != base_content:
            raise StateRecoveryError("durable state changed before clean close")
        journal: JsonObject = {
            "base_sha256": _digest(base_content),
            "final_document": final_document,
            "final_sha256": _digest(final_content),
            "schema_version": 1,
        }
        self.writer.write(self.pending_path, deterministic_json_bytes(journal))
        self.writer.write(self.path, final_content)
        self.pending_path.unlink()
        _fsync_directory(self.pending_path.parent)
