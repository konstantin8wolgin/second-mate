"""Offline trusted-local adapter control plane for CAP-02A."""

from __future__ import annotations

import os
import re
import stat
import uuid
from contextlib import suppress
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol, cast

from second_mate.domain import JsonObject
from second_mate.store import deterministic_json_bytes, strict_json_loads

_RISK_ACKNOWLEDGEMENTS = (
    "broad_local_machine_access",
    "hostile_repository_content_not_contained",
    "outside_effects_not_provable",
)
_MODE = "trusted-local-unsandboxed"
_SPEND_POLICY = "provider-billing-controls-only"
_CLEANUP_POLICY = "exact-private-run-artifacts-only"
_MAX_JSONL_LINE_BYTES = 1024 * 1024


class TrustedLocalAuthorityError(RuntimeError):
    """The trusted-local activation does not match the frozen coordinator basis."""


class TrustedLocalBoundaryError(RuntimeError):
    """The local private-artifact or injected-control boundary is unsafe."""


@dataclass(frozen=True, slots=True)
class OfflineLaunchRequest:
    """The exact private paths a trusted-local control plane may receive."""

    activation_id: str
    repository: Path
    transcript_path: Path
    control_path: Path
    control_identity: tuple[int, int]


class OfflineProcess(Protocol):
    """The process surface consumed by the trusted-local lifecycle."""

    pid: int
    start_token: str
    manages_control_output: bool

    def read_chunk(self) -> bytes | None:
        """Return the next JSONL byte chunk, or ``None`` at end of stream."""

    def wait(self) -> int:
        """Return the mock process exit status."""

    def request_cancel(self) -> None:
        """Request cancellation without claiming that the process stopped."""


class OfflineControlPlane(Protocol):
    """Injected CAP-02A control plane with no production process implementation."""

    offline: bool

    def launch(self, request: OfflineLaunchRequest) -> OfflineProcess:
        """Return one offline process double for the exact launch request."""


@dataclass(frozen=True, slots=True)
class TrustedLocalBasis:
    direction_digest: str
    packet_digest: str
    preflight_digest: str
    repository_id: str
    target_head: str
    target_fingerprint: str
    owner_id: str
    provider_boundary_digest: str


@dataclass(frozen=True, slots=True)
class TrustedLocalRun:
    """One durable CAP-02A mock run and the identities of its private artifacts."""

    activation_id: str
    phase: str
    process_id: int | None
    process_start_token: str | None
    session_id: str | None
    independent_evidence_required: bool
    repository: Path
    run_directory: Path
    artifact_identities: dict[str, tuple[int, int]]


@dataclass(frozen=True, slots=True)
class _TrustedLocalActivation:
    id: str
    granted_by: str
    granted_at: str
    direction_digest: str
    packet_digest: str
    preflight_digest: str
    repository_id: str
    target_head: str
    target_fingerprint: str
    owner_id: str
    provider_boundary_digest: str
    risk_acknowledgements: tuple[str, ...]
    spend_policy: str
    cleanup_policy: str


def _activation_from_json(value: object) -> _TrustedLocalActivation:
    if not isinstance(value, dict):
        raise TrustedLocalAuthorityError("trusted-local activation must be an object")
    expected_keys = {
        "schema_version",
        "id",
        "mode",
        "granted_by",
        "granted_at",
        "bindings",
        "risk_acknowledgements",
        "spend_policy",
        "cleanup_policy",
    }
    if set(value) != expected_keys:
        raise TrustedLocalAuthorityError("trusted-local activation has unexpected fields")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise TrustedLocalAuthorityError("trusted-local activation schema version must be 1")
    if value["mode"] != _MODE:
        raise TrustedLocalAuthorityError(f"trusted-local activation mode must be {_MODE}")
    risks = value["risk_acknowledgements"]
    if not isinstance(risks, list) or tuple(risks) != _RISK_ACKNOWLEDGEMENTS:
        raise TrustedLocalAuthorityError(
            "trusted-local activation risk acknowledgements must be exact"
        )
    if value["spend_policy"] != _SPEND_POLICY:
        raise TrustedLocalAuthorityError(
            f"trusted-local activation spend policy must be {_SPEND_POLICY}"
        )
    if value["cleanup_policy"] != _CLEANUP_POLICY:
        raise TrustedLocalAuthorityError(
            f"trusted-local activation cleanup policy must be {_CLEANUP_POLICY}"
        )
    bindings = value.get("bindings")
    if not isinstance(bindings, dict):
        raise TrustedLocalAuthorityError("trusted-local activation bindings must be an object")
    expected_bindings = {
        "direction_digest",
        "packet_digest",
        "preflight_digest",
        "repository_id",
        "target_head",
        "target_fingerprint",
        "owner_id",
        "provider_boundary_digest",
    }
    if set(bindings) != expected_bindings:
        raise TrustedLocalAuthorityError("trusted-local activation bindings have unexpected fields")

    def text(document: dict[object, object], key: str) -> str:
        item = document.get(key)
        if not isinstance(item, str) or not item:
            raise TrustedLocalAuthorityError(f"trusted-local activation {key} must be text")
        return item

    return _TrustedLocalActivation(
        id=text(value, "id"),
        granted_by=text(value, "granted_by"),
        granted_at=text(value, "granted_at"),
        direction_digest=text(bindings, "direction_digest"),
        packet_digest=text(bindings, "packet_digest"),
        preflight_digest=text(bindings, "preflight_digest"),
        repository_id=text(bindings, "repository_id"),
        target_head=text(bindings, "target_head"),
        target_fingerprint=text(bindings, "target_fingerprint"),
        owner_id=text(bindings, "owner_id"),
        provider_boundary_digest=text(bindings, "provider_boundary_digest"),
        risk_acknowledgements=_RISK_ACKNOWLEDGEMENTS,
        spend_policy=_SPEND_POLICY,
        cleanup_policy=_CLEANUP_POLICY,
    )


_ACTIVATION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_PRIVATE_ARTIFACT_NAMES = ("session.json", "transcript.jsonl", "control.tmp")
_CONSUMED_MARKER_PREFIX = "activation."
_CONSUMED_MARKER_SUFFIX = ".consumed.json"


def _validate_activation_id(value: str) -> None:
    if value in {".", ".."} or _ACTIVATION_ID.fullmatch(value) is None:
        raise TrustedLocalAuthorityError(
            "trusted-local activation id is not a safe private run directory name"
        )


def _real_directory(path: Path, label: str) -> Path:
    try:
        metadata = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise TrustedLocalBoundaryError(f"cannot inspect {label}: {error}") from error
    if not stat.S_ISDIR(metadata.st_mode) or Path(os.path.abspath(path)) != resolved:
        raise TrustedLocalBoundaryError(f"{label} must be an unaliased real directory")
    return resolved


def _private_directory(path: Path, label: str) -> Path:
    resolved = _real_directory(path, label)
    metadata = resolved.stat()
    if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise TrustedLocalBoundaryError(f"{label} must be owned by this user with mode 0700")
    return resolved


def _validate_disjoint(repository: Path, private_root: Path) -> None:
    if (
        repository == private_root
        or repository.is_relative_to(private_root)
        or private_root.is_relative_to(repository)
    ):
        raise TrustedLocalBoundaryError(
            "trusted-local private root and repository must be disjoint"
        )


def _create_private_file(path: Path) -> tuple[int, int]:
    descriptor: int | None = None
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
        )
        os.fchmod(descriptor, 0o600)
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        return (metadata.st_dev, metadata.st_ino)
    except OSError as error:
        raise TrustedLocalBoundaryError(
            f"cannot create private run artifact {path.name}: {error}"
        ) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _write_identified_file(path: Path, identity: tuple[int, int], content: bytes) -> None:
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        metadata = os.fstat(descriptor)
        entry = path.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or (metadata.st_dev, metadata.st_ino) != identity
            or (entry.st_dev, entry.st_ino) != identity
        ):
            raise OSError("private run artifact identity is unsafe")
        os.ftruncate(descriptor, 0)
        remaining = memoryview(content)
        while remaining:
            written = os.write(descriptor, remaining)
            if written == 0:
                raise OSError("short write")
            remaining = remaining[written:]
        os.fsync(descriptor)
    except OSError as error:
        raise TrustedLocalBoundaryError(
            f"cannot safely write private run artifact {path.name}: {error}"
        ) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _validate_identified_file(path: Path, identity: tuple[int, int]) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise TrustedLocalBoundaryError(
            f"cannot inspect private run artifact identity for {path.name}: {error}"
        ) from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or (metadata.st_dev, metadata.st_ino) != identity
    ):
        raise TrustedLocalBoundaryError(f"private run artifact identity changed for {path.name}")


def _append_identified_file(path: Path, identity: tuple[int, int], content: bytes) -> None:
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW | os.O_CLOEXEC)
        metadata = os.fstat(descriptor)
        entry = path.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or (metadata.st_dev, metadata.st_ino) != identity
            or (entry.st_dev, entry.st_ino) != identity
        ):
            raise OSError("private run artifact identity is unsafe")
        remaining = memoryview(content)
        while remaining:
            written = os.write(descriptor, remaining)
            if written == 0:
                raise OSError("short write")
            remaining = remaining[written:]
        os.fsync(descriptor)
    except OSError as error:
        raise TrustedLocalBoundaryError(
            f"cannot safely append private run artifact {path.name}: {error}"
        ) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _read_private_file(path: Path, label: str) -> bytes:
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        metadata = os.fstat(descriptor)
        entry = path.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or (metadata.st_dev, metadata.st_ino) != (entry.st_dev, entry.st_ino)
            or metadata.st_size > _MAX_JSONL_LINE_BYTES
        ):
            raise OSError(f"unsafe {label}")
        with os.fdopen(descriptor, "rb", closefd=True) as stream:
            descriptor = None
            return stream.read()
    except OSError as error:
        raise TrustedLocalBoundaryError(f"cannot safely read {label}: {error}") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _basis_document(basis: TrustedLocalBasis) -> JsonObject:
    return {
        "direction_digest": basis.direction_digest,
        "owner_id": basis.owner_id,
        "packet_digest": basis.packet_digest,
        "preflight_digest": basis.preflight_digest,
        "provider_boundary_digest": basis.provider_boundary_digest,
        "repository_id": basis.repository_id,
        "target_fingerprint": basis.target_fingerprint,
        "target_head": basis.target_head,
    }


def _consumption_document(activation_id: str, basis: TrustedLocalBasis) -> JsonObject:
    return {
        "activation_id": activation_id,
        "basis": _basis_document(basis),
        "cleanup_policy": _CLEANUP_POLICY,
        "mode": _MODE,
        "risk_acknowledgements": list(_RISK_ACKNOWLEDGEMENTS),
        "schema_version": 1,
        "spend_policy": _SPEND_POLICY,
        "state": "consumed",
    }


def _consumption_marker(private_root: Path, activation_id: str) -> Path:
    return private_root / (f"{_CONSUMED_MARKER_PREFIX}{activation_id}{_CONSUMED_MARKER_SUFFIX}")


def _validate_consumption_marker(
    private_root: Path, activation_id: str, basis: TrustedLocalBasis
) -> None:
    marker = _consumption_marker(private_root, activation_id)
    try:
        value = strict_json_loads(_read_private_file(marker, "activation consumption marker"))
    except (ValueError, UnicodeDecodeError) as error:
        raise TrustedLocalBoundaryError(
            f"activation consumption marker is not strict JSON: {error}"
        ) from error
    if value != _consumption_document(activation_id, basis):
        raise TrustedLocalBoundaryError(
            "activation consumption marker does not match the frozen basis"
        )


def _claim_activation(private_root: Path, activation_id: str, basis: TrustedLocalBasis) -> None:
    marker = _consumption_marker(private_root, activation_id)
    content = deterministic_json_bytes(_consumption_document(activation_id, basis))
    descriptor: int | None = None
    try:
        descriptor = os.open(
            marker,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
        )
    except FileExistsError:
        _validate_consumption_marker(private_root, activation_id, basis)
        raise TrustedLocalBoundaryError(
            "trusted-local activation was already consumed and cannot be retried"
        ) from None
    except OSError as error:
        raise TrustedLocalBoundaryError(
            f"cannot claim trusted-local activation: {error}"
        ) from error
    try:
        os.fchmod(descriptor, 0o600)
        remaining = memoryview(content)
        while remaining:
            written = os.write(descriptor, remaining)
            if written == 0:
                raise OSError("short write")
            remaining = remaining[written:]
        os.fsync(descriptor)
    except OSError as error:
        raise TrustedLocalBoundaryError(
            f"cannot persist trusted-local activation claim: {error}"
        ) from error
    finally:
        os.close(descriptor)
    _fsync_directory(private_root)


def _session_document(run: TrustedLocalRun, basis: TrustedLocalBasis) -> JsonObject:
    return {
        "activation_id": run.activation_id,
        "artifact_identities": {
            name: {"device": identity[0], "inode": identity[1]}
            for name, identity in sorted(run.artifact_identities.items())
        },
        "basis": _basis_document(basis),
        "cleanup_policy": _CLEANUP_POLICY,
        "independent_evidence_required": run.independent_evidence_required,
        "phase": run.phase,
        "process": (
            None
            if run.process_id is None or run.process_start_token is None
            else {"id": run.process_id, "start_token": run.process_start_token}
        ),
        "repository": str(run.repository),
        "schema_version": 1,
        "session_id": run.session_id,
    }


def _session_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise TrustedLocalBoundaryError(f"{label} must be an object")
    return cast(dict[str, object], value)


def _session_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise TrustedLocalBoundaryError(f"{label} must be non-empty text")
    return value


def _run_from_session(
    value: object,
    *,
    basis: TrustedLocalBasis,
    activation_id: str,
    repository: Path,
    run_directory: Path,
) -> TrustedLocalRun:
    document = _session_object(value, "trusted-local session")
    expected = {
        "activation_id",
        "artifact_identities",
        "basis",
        "cleanup_policy",
        "independent_evidence_required",
        "phase",
        "process",
        "repository",
        "schema_version",
        "session_id",
    }
    if set(document) != expected:
        raise TrustedLocalBoundaryError("trusted-local session fields are not exact")
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise TrustedLocalBoundaryError("trusted-local session schema version must be 1")
    if document["activation_id"] != activation_id:
        raise TrustedLocalBoundaryError("trusted-local session activation id does not match")
    if document["repository"] != str(repository):
        raise TrustedLocalBoundaryError("trusted-local session repository does not match")
    if document["cleanup_policy"] != _CLEANUP_POLICY:
        raise TrustedLocalBoundaryError("trusted-local session cleanup policy is invalid")
    if document["independent_evidence_required"] is not True:
        raise TrustedLocalBoundaryError("trusted-local session must require independent evidence")

    stored_basis = _session_object(document["basis"], "trusted-local session basis")
    expected_basis = {
        "direction_digest": basis.direction_digest,
        "owner_id": basis.owner_id,
        "packet_digest": basis.packet_digest,
        "preflight_digest": basis.preflight_digest,
        "provider_boundary_digest": basis.provider_boundary_digest,
        "repository_id": basis.repository_id,
        "target_fingerprint": basis.target_fingerprint,
        "target_head": basis.target_head,
    }
    if stored_basis != expected_basis:
        raise TrustedLocalAuthorityError(
            "trusted-local durable session does not match the frozen basis"
        )

    identity_values = _session_object(
        document["artifact_identities"], "trusted-local artifact identities"
    )
    if set(identity_values) != set(_PRIVATE_ARTIFACT_NAMES):
        raise TrustedLocalBoundaryError(
            "trusted-local session must identify exactly its private artifacts"
        )
    identities: dict[str, tuple[int, int]] = {}
    for name in _PRIVATE_ARTIFACT_NAMES:
        identity = _session_object(identity_values[name], f"trusted-local {name} identity")
        if set(identity) != {"device", "inode"}:
            raise TrustedLocalBoundaryError(f"trusted-local {name} identity fields are not exact")
        device = identity["device"]
        inode = identity["inode"]
        if type(device) is not int or device < 0 or type(inode) is not int or inode <= 0:
            raise TrustedLocalBoundaryError(f"trusted-local {name} identity values are invalid")
        identities[name] = (device, inode)

    phase = _session_text(document["phase"], "trusted-local session phase")
    if phase not in {"launching", "running", "unknown-running", "completed", "failed"}:
        raise TrustedLocalBoundaryError("trusted-local session phase is invalid")
    process_value = document["process"]
    if process_value is None:
        process_id = None
        process_start_token = None
    else:
        process = _session_object(process_value, "trusted-local process identity")
        if set(process) != {"id", "start_token"}:
            raise TrustedLocalBoundaryError("trusted-local process identity fields are not exact")
        process_id_value = process["id"]
        if type(process_id_value) is not int or process_id_value <= 0:
            raise TrustedLocalBoundaryError("trusted-local process id is invalid")
        process_id = process_id_value
        process_start_token = _session_text(
            process["start_token"], "trusted-local process start token"
        )
    if phase == "launching" and process_value is not None:
        raise TrustedLocalBoundaryError("launching session cannot claim a process identity")
    if phase in {"running", "completed", "failed"} and process_value is None:
        raise TrustedLocalBoundaryError("trusted-local session omits its process identity")

    session_id_value = document["session_id"]
    if session_id_value is None:
        session_id = None
    else:
        session_id = _session_text(session_id_value, "trusted-local session id")
        try:
            parsed_session_id = uuid.UUID(session_id)
        except ValueError as error:
            raise TrustedLocalBoundaryError("trusted-local session id is invalid") from error
        if str(parsed_session_id) != session_id:
            raise TrustedLocalBoundaryError("trusted-local session id is not canonical")

    return TrustedLocalRun(
        activation_id=activation_id,
        phase=phase,
        process_id=process_id,
        process_start_token=process_start_token,
        session_id=session_id,
        independent_evidence_required=True,
        repository=repository,
        run_directory=run_directory,
        artifact_identities=identities,
    )


class _JsonlLifecycle:
    def __init__(self) -> None:
        self.stage = "thread"
        self.session_id: str | None = None
        self.terminal: str | None = None
        self.invalid = False

    def consume(self, line: bytes) -> None:
        if self.invalid or self.terminal is not None:
            self.invalid = True
            return
        try:
            value = strict_json_loads(line)
        except (ValueError, UnicodeDecodeError):
            self.invalid = True
            return
        if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
            self.invalid = True
            return
        event_type = value.get("type")
        if not isinstance(event_type, str):
            self.invalid = True
            return
        if self.stage == "thread":
            session_id = value.get("thread_id")
            if event_type != "thread.started" or not isinstance(session_id, str):
                self.invalid = True
                return
            try:
                parsed_id = uuid.UUID(session_id)
            except ValueError:
                self.invalid = True
                return
            if str(parsed_id) != session_id:
                self.invalid = True
                return
            self.session_id = session_id
            self.stage = "turn"
            return
        if self.stage == "turn":
            if event_type != "turn.started":
                self.invalid = True
                return
            self.stage = "active"
            return
        if event_type in {"item.started", "item.updated", "item.completed"}:
            if not isinstance(value.get("item"), dict):
                self.invalid = True
            return
        if event_type == "turn.completed":
            self.terminal = "completed"
            return
        if event_type == "turn.failed" and isinstance(value.get("error"), dict):
            self.terminal = "failed"
            return
        self.invalid = True


class OfflineTrustedLocalAdapter:
    """Validate one activation before handing control to an injected offline process."""

    def __init__(self, control_plane: OfflineControlPlane) -> None:
        self._control_plane = control_plane
        self._processes: dict[str, OfflineProcess] = {}
        self._bases: dict[str, TrustedLocalBasis] = {}

    def _validate_control_plane(self, *, basis: TrustedLocalBasis, repository: Path) -> None:
        del basis, repository
        if self._control_plane.offline is not True:
            raise TrustedLocalBoundaryError("CAP-02A requires an explicitly offline control plane")

    def start(
        self,
        *,
        basis: TrustedLocalBasis,
        activation_data: object,
        repository: Path,
        private_root: Path,
    ) -> TrustedLocalRun:
        activation = _activation_from_json(activation_data)
        _validate_activation_id(activation.id)
        comparisons = (
            ("direction digest", activation.direction_digest, basis.direction_digest),
            ("packet digest", activation.packet_digest, basis.packet_digest),
            ("preflight digest", activation.preflight_digest, basis.preflight_digest),
            ("repository id", activation.repository_id, basis.repository_id),
            ("target head", activation.target_head, basis.target_head),
            ("target fingerprint", activation.target_fingerprint, basis.target_fingerprint),
            ("owner id", activation.owner_id, basis.owner_id),
            (
                "provider boundary digest",
                activation.provider_boundary_digest,
                basis.provider_boundary_digest,
            ),
        )
        for label, actual, expected in comparisons:
            if actual != expected:
                raise TrustedLocalAuthorityError(
                    f"trusted-local activation {label} does not match the frozen basis"
                )
        repository_path = _real_directory(repository, "trusted-local repository")
        private_root_path = _private_directory(private_root, "trusted-local private root")
        _validate_disjoint(repository_path, private_root_path)
        self._validate_control_plane(basis=basis, repository=repository_path)
        _claim_activation(private_root_path, activation.id, basis)

        run_directory = private_root_path / activation.id
        try:
            os.mkdir(run_directory, 0o700)
            os.chmod(run_directory, 0o700)
            _fsync_directory(private_root_path)
        except OSError as error:
            raise TrustedLocalBoundaryError(
                f"cannot create private run directory: {error}"
            ) from error

        identities = {
            name: _create_private_file(run_directory / name) for name in _PRIVATE_ARTIFACT_NAMES
        }
        _fsync_directory(run_directory)
        request = OfflineLaunchRequest(
            activation_id=activation.id,
            repository=repository_path,
            transcript_path=run_directory / "transcript.jsonl",
            control_path=run_directory / "control.tmp",
            control_identity=identities["control.tmp"],
        )
        launching = TrustedLocalRun(
            activation_id=activation.id,
            phase="launching",
            process_id=None,
            process_start_token=None,
            session_id=None,
            independent_evidence_required=True,
            repository=repository_path,
            run_directory=run_directory,
            artifact_identities=identities,
        )
        self._bases[activation.id] = basis
        self._persist(launching)
        try:
            process = self._control_plane.launch(request)
        except Exception:
            unknown = replace(launching, phase="unknown-running")
            self._persist(unknown)
            return unknown
        if (
            type(process.pid) is not int
            or process.pid <= 0
            or not isinstance(process.start_token, str)
            or not process.start_token
        ):
            unknown = replace(launching, phase="unknown-running")
            self._persist(unknown)
            return unknown
        run = replace(
            launching,
            phase="running",
            process_id=process.pid,
            process_start_token=process.start_token,
        )
        self._processes[activation.id] = process
        self._persist(run)
        return run

    def _persist(self, run: TrustedLocalRun) -> None:
        basis = self._bases.get(run.activation_id)
        if basis is None:
            raise TrustedLocalBoundaryError("trusted-local run basis is unavailable")
        _write_identified_file(
            run.run_directory / "session.json",
            run.artifact_identities["session.json"],
            deterministic_json_bytes(_session_document(run, basis)),
        )

    def load(
        self,
        *,
        basis: TrustedLocalBasis,
        activation_id: str,
        repository: Path,
        private_root: Path,
    ) -> TrustedLocalRun:
        """Reload one private run without assuming control of its former process."""

        _validate_activation_id(activation_id)
        repository_path = _real_directory(repository, "trusted-local repository")
        private_root_path = _private_directory(private_root, "trusted-local private root")
        _validate_disjoint(repository_path, private_root_path)
        _validate_consumption_marker(private_root_path, activation_id, basis)
        run_directory = _private_directory(
            private_root_path / activation_id, "trusted-local run directory"
        )
        try:
            entries = {path.name: path for path in run_directory.iterdir()}
        except OSError as error:
            raise TrustedLocalBoundaryError(
                f"cannot enumerate private run artifacts: {error}"
            ) from error
        if set(entries) != set(_PRIVATE_ARTIFACT_NAMES):
            raise TrustedLocalBoundaryError(
                "private run directory must contain exactly the recorded artifacts"
            )
        session_content = _read_private_file(entries["session.json"], "trusted-local session")
        try:
            session_value = strict_json_loads(session_content)
        except (ValueError, UnicodeDecodeError) as error:
            raise TrustedLocalBoundaryError(
                f"trusted-local session is not strict JSON: {error}"
            ) from error
        run = _run_from_session(
            session_value,
            basis=basis,
            activation_id=activation_id,
            repository=repository_path,
            run_directory=run_directory,
        )
        for name in _PRIVATE_ARTIFACT_NAMES:
            _validate_identified_file(entries[name], run.artifact_identities[name])
        self._bases[activation_id] = basis
        if run.phase in {"launching", "running"}:
            run = replace(run, phase="unknown-running")
            self._persist(run)
        return run

    def finish(self, run: TrustedLocalRun) -> TrustedLocalRun:
        """Drain one injected JSONL stream and persist its conservative terminal state."""

        if run.phase != "running":
            return run
        process = self._processes.get(run.activation_id)
        if (
            process is None
            or process.pid != run.process_id
            or process.start_token != run.process_start_token
        ):
            unknown = replace(run, phase="unknown-running")
            self._persist(unknown)
            return unknown

        lifecycle = _JsonlLifecycle()
        buffer = b""
        discarding_oversized_line = False
        stream_failed = False
        transcript_path = run.run_directory / "transcript.jsonl"
        control_path = run.run_directory / "control.tmp"
        try:
            while True:
                chunk = process.read_chunk()
                if chunk is None:
                    break
                if not isinstance(chunk, bytes) or not chunk:
                    stream_failed = True
                    break
                _append_identified_file(
                    transcript_path,
                    run.artifact_identities["transcript.jsonl"],
                    chunk,
                )
                cursor = 0
                while cursor < len(chunk):
                    newline = chunk.find(b"\n", cursor)
                    complete_line = newline >= 0
                    segment_end = newline if complete_line else len(chunk)
                    segment_size = segment_end - cursor
                    if discarding_oversized_line:
                        if complete_line:
                            discarding_oversized_line = False
                            cursor = newline + 1
                            continue
                        break
                    if len(buffer) + segment_size > _MAX_JSONL_LINE_BYTES:
                        lifecycle.invalid = True
                        buffer = b""
                        if not complete_line:
                            discarding_oversized_line = True
                            break
                        cursor = newline + 1
                        continue
                    buffer += chunk[cursor:segment_end]
                    if not complete_line:
                        break
                    if not buffer:
                        lifecycle.invalid = True
                    else:
                        lifecycle.consume(buffer)
                    buffer = b""
                    if lifecycle.session_id is not None and run.session_id is None:
                        run = replace(run, session_id=lifecycle.session_id)
                        self._persist(run)
                    cursor = newline + 1
                if not process.manages_control_output:
                    _write_identified_file(
                        control_path,
                        run.artifact_identities["control.tmp"],
                        buffer,
                    )
            if buffer or discarding_oversized_line:
                lifecycle.invalid = True
            exit_code = process.wait()
            if type(exit_code) is not int:
                stream_failed = True
        except Exception:
            stream_failed = True
            exit_code = None

        if (
            not stream_failed
            and not lifecycle.invalid
            and lifecycle.terminal == "completed"
            and exit_code == 0
        ):
            phase = "completed"
        elif (
            not stream_failed
            and not lifecycle.invalid
            and lifecycle.terminal == "failed"
            and type(exit_code) is int
            and exit_code > 0
        ):
            phase = "failed"
        else:
            phase = "unknown-running"
        finished = replace(run, phase=phase, session_id=lifecycle.session_id or run.session_id)
        self._persist(finished)
        if phase != "unknown-running":
            self._processes.pop(run.activation_id, None)
        return finished

    def cancel(self, run: TrustedLocalRun) -> TrustedLocalRun:
        """Request cancellation while preserving ambiguity and every recovery artifact."""

        if run.phase != "running":
            return run
        process = self._processes.get(run.activation_id)
        if (
            process is not None
            and process.pid == run.process_id
            and process.start_token == run.process_start_token
        ):
            with suppress(Exception):
                process.request_cancel()
        self._processes.pop(run.activation_id, None)
        unknown = replace(run, phase="unknown-running")
        self._persist(unknown)
        return unknown

    def cleanup(self, run: TrustedLocalRun) -> None:
        """Delete only the exact, still-identical local artifacts recorded for one run."""

        _validate_activation_id(run.activation_id)
        if set(run.artifact_identities) != set(_PRIVATE_ARTIFACT_NAMES):
            raise TrustedLocalBoundaryError(
                "private run identity record must name exactly the cleanup artifacts"
            )
        repository = _real_directory(run.repository, "trusted-local repository")
        private_root = _private_directory(run.run_directory.parent, "trusted-local private root")
        run_directory = _private_directory(run.run_directory, "trusted-local run directory")
        _validate_disjoint(repository, private_root)
        basis = self._bases.get(run.activation_id)
        if basis is None:
            raise TrustedLocalBoundaryError(
                "trusted-local cleanup requires a validated durable session record"
            )
        _validate_consumption_marker(private_root, run.activation_id, basis)
        if run_directory != private_root / run.activation_id:
            raise TrustedLocalBoundaryError(
                "private run directory does not match the activation identity"
            )
        try:
            entries = {path.name: path for path in run_directory.iterdir()}
        except OSError as error:
            raise TrustedLocalBoundaryError(
                f"cannot enumerate private run artifacts: {error}"
            ) from error
        if set(entries) != set(_PRIVATE_ARTIFACT_NAMES):
            raise TrustedLocalBoundaryError(
                "private run directory must contain exactly the recorded artifacts"
            )

        # The complete set and every physical identity are checked before the first unlink.
        for name in _PRIVATE_ARTIFACT_NAMES:
            _validate_identified_file(entries[name], run.artifact_identities[name])
        try:
            stored_session = strict_json_loads(
                _read_private_file(entries["session.json"], "trusted-local session")
            )
        except (ValueError, UnicodeDecodeError) as error:
            raise TrustedLocalBoundaryError(
                f"trusted-local cleanup session record is invalid: {error}"
            ) from error
        expected_session = _session_document(run, basis)
        if stored_session != expected_session:
            raise TrustedLocalBoundaryError(
                "trusted-local cleanup session record does not match the requested run"
            )
        directory_descriptor: int | None = None
        try:
            directory_descriptor = os.open(
                run_directory,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            )
            for name in ("transcript.jsonl", "control.tmp", "session.json"):
                _validate_identified_file(entries[name], run.artifact_identities[name])
                os.unlink(name, dir_fd=directory_descriptor)
        except OSError as error:
            raise TrustedLocalBoundaryError(
                f"cannot remove exact private run artifact: {error}"
            ) from error
        finally:
            if directory_descriptor is not None:
                os.close(directory_descriptor)
        try:
            os.rmdir(run_directory)
            _fsync_directory(private_root)
        except OSError as error:
            raise TrustedLocalBoundaryError(
                f"cannot remove empty private run directory: {error}"
            ) from error
