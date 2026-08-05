from __future__ import annotations

import copy
import json
import os
import stat
from pathlib import Path

import pytest

from second_mate import trusted_local as trusted_local_module
from second_mate.trusted_local import (
    OfflineLaunchRequest,
    OfflineProcess,
    OfflineTrustedLocalAdapter,
    TrustedLocalAuthorityError,
    TrustedLocalBasis,
    TrustedLocalBoundaryError,
    TrustedLocalRun,
)


class RecordingControlPlane:
    offline = True

    def __init__(self) -> None:
        self.launch_count = 0

    def launch(self, request: object) -> object:
        self.launch_count += 1
        raise AssertionError("an authority mismatch must not launch the control plane")


class IdleOfflineProcess:
    pid = 4242
    start_token = "mock-process-start-1"
    manages_control_output = False

    def read_chunk(self) -> bytes | None:
        return None

    def wait(self) -> int:
        return 0

    def request_cancel(self) -> None:
        raise AssertionError("this test does not cancel the offline process")


class LaunchingControlPlane:
    offline = True

    def __init__(self, process: OfflineProcess | None = None) -> None:
        self.launch_count = 0
        self.request: OfflineLaunchRequest | None = None
        self.process = process if process is not None else IdleOfflineProcess()

    def launch(self, request: OfflineLaunchRequest) -> OfflineProcess:
        self.launch_count += 1
        self.request = request
        return self.process


class AmbiguousLaunchControlPlane:
    offline = True

    def __init__(self) -> None:
        self.launch_count = 0

    def launch(self, request: OfflineLaunchRequest) -> OfflineProcess:
        self.launch_count += 1
        raise RuntimeError("mock lost contact after launch request")


class ScriptedOfflineProcess:
    pid = 8484
    start_token = "mock-process-start-2"
    manages_control_output = False

    def __init__(self, chunks: list[bytes], exit_code: int) -> None:
        self._chunks = list(chunks)
        self._exit_code = exit_code
        self.cancel_requested = False
        self.read_count = 0
        self.wait_count = 0

    def read_chunk(self) -> bytes | None:
        self.read_count += 1
        return self._chunks.pop(0) if self._chunks else None

    def wait(self) -> int:
        self.wait_count += 1
        return self._exit_code

    def request_cancel(self) -> None:
        self.cancel_requested = True


class FailingOfflineProcess(ScriptedOfflineProcess):
    def __init__(self, failure: str) -> None:
        super().__init__([], exit_code=0)
        self._failure = failure

    def read_chunk(self) -> bytes | None:
        if self._failure == "read":
            raise OSError("mock stream disappeared")
        return None

    def wait(self) -> int:
        if self._failure == "wait":
            raise OSError("mock process identity disappeared")
        return 0


def _start_mock_run(
    repository: Path, private_root: Path
) -> tuple[OfflineTrustedLocalAdapter, TrustedLocalRun, LaunchingControlPlane]:
    control_plane = LaunchingControlPlane()
    adapter = OfflineTrustedLocalAdapter(control_plane)
    run = adapter.start(
        basis=_basis(),
        activation_data=_activation(),
        repository=repository,
        private_root=private_root,
    )
    assert isinstance(run, TrustedLocalRun)
    return adapter, run, control_plane


def _basis() -> TrustedLocalBasis:
    return TrustedLocalBasis(
        direction_digest="d" * 64,
        packet_digest="a" * 64,
        preflight_digest="b" * 64,
        repository_id="repository-1",
        target_head="1" * 40,
        target_fingerprint="c" * 64,
        owner_id="owner-1",
        provider_boundary_digest="e" * 64,
    )


def _activation() -> dict[str, object]:
    basis = _basis()
    return {
        "schema_version": 1,
        "id": "run-001",
        "mode": "trusted-local-unsandboxed",
        "granted_by": "human-operator",
        "granted_at": "2026-08-04T20:00:00Z",
        "bindings": {
            "direction_digest": basis.direction_digest,
            "packet_digest": basis.packet_digest,
            "preflight_digest": basis.preflight_digest,
            "repository_id": basis.repository_id,
            "target_head": basis.target_head,
            "target_fingerprint": basis.target_fingerprint,
            "owner_id": basis.owner_id,
            "provider_boundary_digest": basis.provider_boundary_digest,
        },
        "risk_acknowledgements": [
            "broad_local_machine_access",
            "hostile_repository_content_not_contained",
            "outside_effects_not_provable",
        ],
        "spend_policy": "provider-billing-controls-only",
        "cleanup_policy": "exact-private-run-artifacts-only",
    }


def _private_root(path: Path) -> Path:
    path.mkdir(mode=0o700)
    os.chmod(path, 0o700)
    return path


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("direction_digest", "direction digest"),
        ("packet_digest", "packet digest"),
        ("preflight_digest", "preflight digest"),
        ("repository_id", "repository id"),
        ("target_head", "target head"),
        ("target_fingerprint", "target fingerprint"),
        ("owner_id", "owner id"),
        ("provider_boundary_digest", "provider boundary digest"),
    ],
)
def test_authority_mismatch_refuses_before_private_state_or_launch(
    tmp_path: Path, field: str, message: str
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    activation = _activation()
    bindings = activation["bindings"]
    assert isinstance(bindings, dict)
    bindings[field] = "mismatched-authority-value"
    control_plane = RecordingControlPlane()

    with pytest.raises(TrustedLocalAuthorityError, match=message):
        OfflineTrustedLocalAdapter(control_plane).start(
            basis=_basis(),
            activation_data=activation,
            repository=repository,
            private_root=private_root,
        )

    assert control_plane.launch_count == 0
    assert tuple(private_root.iterdir()) == ()


def test_activation_rejects_a_second_mate_token_cap(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    activation = _activation()
    activation["token_limit"] = 10_000
    control_plane = RecordingControlPlane()

    with pytest.raises(TrustedLocalAuthorityError, match="unexpected fields"):
        OfflineTrustedLocalAdapter(control_plane).start(
            basis=_basis(),
            activation_data=activation,
            repository=repository,
            private_root=private_root,
        )

    assert control_plane.launch_count == 0
    assert tuple(private_root.iterdir()) == ()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", 2, "schema version"),
        ("mode", "sandboxed", "mode"),
        (
            "risk_acknowledgements",
            ["broad_local_machine_access", "outside_effects_not_provable"],
            "risk acknowledgements",
        ),
        ("spend_policy", "second-mate-token-cap", "spend policy"),
        ("cleanup_policy", "recursive-cleanup", "cleanup policy"),
    ],
)
def test_activation_requires_exact_poc_policies(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    activation = copy.deepcopy(_activation())
    activation[field] = value
    control_plane = RecordingControlPlane()

    with pytest.raises(TrustedLocalAuthorityError, match=message):
        OfflineTrustedLocalAdapter(control_plane).start(
            basis=_basis(),
            activation_data=activation,
            repository=repository,
            private_root=private_root,
        )

    assert control_plane.launch_count == 0
    assert tuple(private_root.iterdir()) == ()


def test_non_offline_control_plane_refuses_before_private_state_or_launch(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    control_plane = RecordingControlPlane()
    control_plane.offline = False

    with pytest.raises(TrustedLocalBoundaryError, match="offline control plane"):
        OfflineTrustedLocalAdapter(control_plane).start(
            basis=_basis(),
            activation_data=_activation(),
            repository=repository,
            private_root=private_root,
        )

    assert control_plane.launch_count == 0
    assert tuple(private_root.iterdir()) == ()


def test_private_root_inside_repository_refuses_before_launch(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(repository / "private")
    control_plane = RecordingControlPlane()

    with pytest.raises(TrustedLocalBoundaryError, match="must be disjoint"):
        OfflineTrustedLocalAdapter(control_plane).start(
            basis=_basis(),
            activation_data=_activation(),
            repository=repository,
            private_root=private_root,
        )

    assert control_plane.launch_count == 0
    assert tuple(private_root.iterdir()) == ()


def test_matching_activation_creates_exact_private_run_envelope_and_launches_mock(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    control_plane = LaunchingControlPlane()

    run = OfflineTrustedLocalAdapter(control_plane).start(
        basis=_basis(),
        activation_data=_activation(),
        repository=repository,
        private_root=private_root,
    )

    assert isinstance(run, TrustedLocalRun)
    assert run.activation_id == "run-001"
    assert run.phase == "running"
    assert run.process_id == 4242
    assert run.process_start_token == "mock-process-start-1"
    assert run.session_id is None
    assert run.independent_evidence_required is True
    assert control_plane.launch_count == 1
    assert control_plane.request == OfflineLaunchRequest(
        activation_id="run-001",
        repository=repository.resolve(strict=True),
        transcript_path=private_root / "run-001" / "transcript.jsonl",
        control_path=private_root / "run-001" / "control.tmp",
        control_identity=run.artifact_identities["control.tmp"],
    )

    run_directory = private_root / "run-001"
    assert stat.S_IMODE(run_directory.stat().st_mode) == 0o700
    assert {path.name for path in run_directory.iterdir()} == {
        "session.json",
        "transcript.jsonl",
        "control.tmp",
    }
    for path in run_directory.iterdir():
        metadata = path.lstat()
        assert stat.S_ISREG(metadata.st_mode)
        assert metadata.st_nlink == 1
        assert metadata.st_uid == os.geteuid()
        assert stat.S_IMODE(metadata.st_mode) == 0o600

    assert run.artifact_identities == {
        path.name: (path.stat().st_dev, path.stat().st_ino) for path in run_directory.iterdir()
    }


def test_existing_run_owner_refuses_a_second_launch(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    _, first_run, first_control = _start_mock_run(repository, private_root)
    competing_control = LaunchingControlPlane()

    with pytest.raises(TrustedLocalBoundaryError, match="already consumed"):
        OfflineTrustedLocalAdapter(competing_control).start(
            basis=_basis(),
            activation_data=_activation(),
            repository=repository,
            private_root=private_root,
        )

    assert first_control.launch_count == 1
    assert competing_control.launch_count == 0
    assert first_run.phase == "running"
    assert {path.name for path in first_run.run_directory.iterdir()} == {
        "session.json",
        "transcript.jsonl",
        "control.tmp",
    }


def test_cleanup_removes_only_the_exact_identified_run_artifacts(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    repository_sentinel = repository / "work.txt"
    repository_sentinel.write_text("preserve repository work\n", encoding="utf-8")
    private_root = _private_root(tmp_path / "private")
    sibling = private_root / "another-run.keep"
    sibling.write_text("preserve sibling\n", encoding="utf-8")
    transcript = b"".join(
        (
            _event_line(
                {
                    "type": "thread.started",
                    "thread_id": "019fcdda-2c17-7f51-9e81-a56f5b9585dc",
                }
            ),
            _event_line({"type": "turn.started"}),
            _event_line({"type": "turn.completed"}),
        )
    )
    adapter = OfflineTrustedLocalAdapter(
        LaunchingControlPlane(ScriptedOfflineProcess([transcript], exit_code=0))
    )
    started = adapter.start(
        basis=_basis(),
        activation_data=_activation(),
        repository=repository,
        private_root=private_root,
    )
    run = adapter.finish(started)

    adapter.cleanup(run)

    assert not run.run_directory.exists()
    assert repository_sentinel.read_text(encoding="utf-8") == "preserve repository work\n"
    assert sibling.read_text(encoding="utf-8") == "preserve sibling\n"


@pytest.mark.parametrize(
    ("failure_name", "remaining_names"),
    [
        (
            "transcript.jsonl",
            {"transcript.jsonl", "control.tmp", "session.json"},
        ),
        ("control.tmp", {"control.tmp", "session.json"}),
        ("session.json", {"session.json"}),
    ],
)
def test_interrupted_cleanup_persists_intent_and_fresh_reload_resumes_exact_remainder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_name: str,
    remaining_names: set[str],
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    repository_sentinel = repository / "work.txt"
    repository_sentinel.write_text("preserve repository work\n", encoding="utf-8")
    private_root = _private_root(tmp_path / "private")
    private_sentinel = private_root / "another-run.keep"
    private_sentinel.write_text("preserve sibling\n", encoding="utf-8")
    process = ScriptedOfflineProcess(
        [
            _event_line(
                {
                    "type": "thread.started",
                    "thread_id": "019fcdda-2c17-7f51-9e81-a56f5b9585dc",
                }
            )
            + _event_line({"type": "turn.started"})
            + _event_line({"type": "turn.completed"})
        ],
        exit_code=0,
    )
    adapter = OfflineTrustedLocalAdapter(LaunchingControlPlane(process))
    run = adapter.finish(
        adapter.start(
            basis=_basis(),
            activation_data=_activation(),
            repository=repository,
            private_root=private_root,
        )
    )
    real_unlink = os.unlink

    def interrupt_cleanup(path: str, *, dir_fd: int | None = None) -> None:
        if path == failure_name:
            raise OSError(f"injected interruption before {failure_name}")
        real_unlink(path, dir_fd=dir_fd)

    with monkeypatch.context() as context:
        context.setattr("second_mate.trusted_local.os.unlink", interrupt_cleanup)
        with pytest.raises(TrustedLocalBoundaryError, match="cannot remove exact"):
            adapter.cleanup(run)

    assert {path.name for path in run.run_directory.iterdir()} == remaining_names
    session = trusted_local_module._read_durable_json(
        run.run_directory / "session.json", "test session"
    )
    assert isinstance(session, dict)
    assert session["phase"] == "cleanup-pending"

    recovery = OfflineTrustedLocalAdapter(LaunchingControlPlane())
    pending = recovery.load(
        basis=_basis(),
        activation_id=run.activation_id,
        repository=repository,
        private_root=private_root,
    )
    assert pending.phase == "cleanup-pending"
    recovery.cleanup(pending)

    assert not run.run_directory.exists()
    assert (private_root / "activation.run-001.consumed.json").is_file()
    assert repository_sentinel.read_text(encoding="utf-8") == "preserve repository work\n"
    assert private_sentinel.read_text(encoding="utf-8") == "preserve sibling\n"


@pytest.mark.parametrize(
    "partial_bytes",
    [11, trusted_local_module._DURABLE_RECORD_HEADER_BYTES + 17],
)
def test_cleanup_intent_write_interruption_preserves_reloadable_previous_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, partial_bytes: int
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    repository_sentinel = repository / "work.txt"
    repository_sentinel.write_text("preserve repository work\n", encoding="utf-8")
    private_root = _private_root(tmp_path / "private")
    private_sentinel = private_root / "another-run.keep"
    private_sentinel.write_text("preserve sibling\n", encoding="utf-8")
    adapter, running, _ = _start_mock_run(repository, private_root)
    run = adapter.cancel(running)
    session_path = run.run_directory / "session.json"
    real_write = os.write
    interrupted = False

    def interrupt_session_write(descriptor: int, content: bytes | memoryview) -> int:
        nonlocal interrupted
        descriptor_path = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
        if not interrupted and descriptor_path == session_path:
            interrupted = True
            real_write(descriptor, content[:partial_bytes])
            raise OSError("injected interruption during cleanup intent persistence")
        return real_write(descriptor, content)

    with monkeypatch.context() as context:
        context.setattr("second_mate.trusted_local.os.write", interrupt_session_write)
        with pytest.raises(TrustedLocalBoundaryError, match="cannot safely append"):
            adapter.cleanup(run, recovery_disposition="abandoned")

    assert interrupted is True
    recovery = OfflineTrustedLocalAdapter(LaunchingControlPlane())
    recovered = recovery.load(
        basis=_basis(),
        activation_id=run.activation_id,
        repository=repository,
        private_root=private_root,
    )
    assert recovered.phase == "unknown-running"
    recovery.cleanup(recovered, recovery_disposition="abandoned")

    assert not run.run_directory.exists()
    assert (private_root / "activation.run-001.consumed.json").is_file()
    assert repository_sentinel.read_text(encoding="utf-8") == "preserve repository work\n"
    assert private_sentinel.read_text(encoding="utf-8") == "preserve sibling\n"


@pytest.mark.parametrize(
    "partial_bytes",
    [13, trusted_local_module._DURABLE_RECORD_HEADER_BYTES + 19],
)
def test_cleanup_authorization_write_interruption_preserves_reloadable_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, partial_bytes: int
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    repository_sentinel = repository / "work.txt"
    repository_sentinel.write_text("preserve repository work\n", encoding="utf-8")
    private_root = _private_root(tmp_path / "private")
    private_sentinel = private_root / "another-run.keep"
    private_sentinel.write_text("preserve sibling\n", encoding="utf-8")
    adapter, running, _ = _start_mock_run(repository, private_root)
    run = adapter.cancel(running)
    marker_path = private_root / "activation.run-001.consumed.json"
    real_write = os.write
    interrupted = False

    def interrupt_marker_write(descriptor: int, content: bytes | memoryview) -> int:
        nonlocal interrupted
        descriptor_path = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
        if not interrupted and descriptor_path == marker_path:
            interrupted = True
            real_write(descriptor, content[:partial_bytes])
            raise OSError("injected interruption during cleanup authorization persistence")
        return real_write(descriptor, content)

    with monkeypatch.context() as context:
        context.setattr("second_mate.trusted_local.os.write", interrupt_marker_write)
        with pytest.raises(TrustedLocalBoundaryError, match="cannot safely append"):
            adapter.cleanup(run, recovery_disposition="abandoned")

    assert interrupted is True
    recovery = OfflineTrustedLocalAdapter(LaunchingControlPlane())
    pending = recovery.load(
        basis=_basis(),
        activation_id=run.activation_id,
        repository=repository,
        private_root=private_root,
    )
    assert pending.phase == "cleanup-pending"
    recovery.cleanup(pending)

    assert not run.run_directory.exists()
    assert marker_path.is_file()
    assert repository_sentinel.read_text(encoding="utf-8") == "preserve repository work\n"
    assert private_sentinel.read_text(encoding="utf-8") == "preserve sibling\n"


@pytest.mark.parametrize("record_name", ["session", "marker"])
@pytest.mark.parametrize(
    ("suffix", "message"),
    [
        (
            trusted_local_module._DURABLE_RECORD_PREFIX + b"00000003 " + (b"0" * 64) + b"\n{}\n",
            "digest",
        ),
        (trusted_local_module._DURABLE_RECORD_PREFIX + b"00000000 ", "length"),
        (trusted_local_module._DURABLE_RECORD_PREFIX + b"ffffffff ", "length"),
        (trusted_local_module._DURABLE_RECORD_PREFIX + b"f", "length"),
        (trusted_local_module._DURABLE_RECORD_PREFIX + b"0011", "length"),
        (trusted_local_module._DURABLE_RECORD_PREFIX + b"00100000 ", "length"),
        (b"not-a-durable-frame", "non-frame"),
    ],
)
def test_cleanup_record_complete_corruption_fails_closed_without_deletion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    record_name: str,
    suffix: bytes,
    message: str,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    repository_sentinel = repository / "work.txt"
    repository_sentinel.write_text("preserve repository work\n", encoding="utf-8")
    private_root = _private_root(tmp_path / "private")
    private_sentinel = private_root / "another-run.keep"
    private_sentinel.write_text("preserve sibling\n", encoding="utf-8")
    adapter, running, _ = _start_mock_run(repository, private_root)
    run = adapter.cancel(running)

    def interrupt_before_first_unlink(path: str, *, dir_fd: int | None = None) -> None:
        del dir_fd
        raise OSError(f"injected interruption before {path}")

    with monkeypatch.context() as context:
        context.setattr("second_mate.trusted_local.os.unlink", interrupt_before_first_unlink)
        with pytest.raises(TrustedLocalBoundaryError, match="cannot remove exact"):
            adapter.cleanup(run, recovery_disposition="abandoned")

    if record_name == "session":
        record_path = run.run_directory / "session.json"
    else:
        record_path = private_root / "activation.run-001.consumed.json"
    with record_path.open("ab") as stream:
        stream.write(suffix)
        stream.flush()
        os.fsync(stream.fileno())

    recovery = OfflineTrustedLocalAdapter(LaunchingControlPlane())
    with pytest.raises(TrustedLocalBoundaryError, match=message):
        recovery.load(
            basis=_basis(),
            activation_id=run.activation_id,
            repository=repository,
            private_root=private_root,
        )

    assert {path.name for path in run.run_directory.iterdir()} == {
        "session.json",
        "transcript.jsonl",
        "control.tmp",
    }
    assert repository_sentinel.read_text(encoding="utf-8") == "preserve repository work\n"
    assert private_sentinel.read_text(encoding="utf-8") == "preserve sibling\n"


def test_durable_record_initial_scan_is_bounded_for_newline_dense_invalid_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    strict_parse_count = 0
    real_strict_json_loads = trusted_local_module.strict_json_loads

    def count_strict_parse(content: str | bytes) -> object:
        nonlocal strict_parse_count
        strict_parse_count += 1
        return real_strict_json_loads(content)

    monkeypatch.setattr(trusted_local_module, "strict_json_loads", count_strict_parse)

    with pytest.raises(TrustedLocalBoundaryError, match="no complete strict JSON"):
        trusted_local_module._decode_durable_json_records(
            b"{" + (b"\n" * 4096), "newline-dense record"
        )

    assert strict_parse_count <= 1


def test_durable_record_near_capacity_rejects_even_a_partial_magic_prefix() -> None:
    initial_record = b"{}\n"
    content = (
        initial_record
        + (b" " * (trusted_local_module._MAX_JSONL_LINE_BYTES - len(initial_record) - 1))
        + trusted_local_module._DURABLE_RECORD_PREFIX[:1]
    )

    with pytest.raises(TrustedLocalBoundaryError, match="length"):
        trusted_local_module._decode_durable_json_records(content, "near-capacity record")


@pytest.mark.parametrize("record_name", ["session", "marker"])
def test_cleanup_retry_resyncs_a_visible_record_after_ambiguous_fsync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    record_name: str,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    private_sentinel = private_root / "another-run.keep"
    private_sentinel.write_text("preserve sibling\n", encoding="utf-8")
    adapter, running, _ = _start_mock_run(repository, private_root)
    run = adapter.cancel(running)
    if record_name == "session":
        record_path = run.run_directory / "session.json"
    else:
        record_path = private_root / "activation.run-001.consumed.json"
    real_fsync = os.fsync
    interrupted = False

    def fail_target_fsync_once(descriptor: int) -> None:
        nonlocal interrupted
        descriptor_path = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
        if not interrupted and descriptor_path == record_path:
            interrupted = True
            raise OSError("injected ambiguous durable-record fsync")
        real_fsync(descriptor)

    with monkeypatch.context() as context:
        context.setattr("second_mate.trusted_local.os.fsync", fail_target_fsync_once)
        with pytest.raises(TrustedLocalBoundaryError, match="cannot safely append"):
            adapter.cleanup(run, recovery_disposition="abandoned")

    assert interrupted is True
    recovery = OfflineTrustedLocalAdapter(LaunchingControlPlane())
    pending = recovery.load(
        basis=_basis(),
        activation_id=run.activation_id,
        repository=repository,
        private_root=private_root,
    )
    assert pending.phase == "cleanup-pending"

    def fail_target_fsync(descriptor: int) -> None:
        descriptor_path = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
        if descriptor_path == record_path:
            raise OSError("injected repeated durable-record fsync failure")
        real_fsync(descriptor)

    with monkeypatch.context() as context:
        context.setattr("second_mate.trusted_local.os.fsync", fail_target_fsync)
        with pytest.raises(TrustedLocalBoundaryError, match="cannot safely sync"):
            recovery.cleanup(pending)

    assert {path.name for path in run.run_directory.iterdir()} == {
        "session.json",
        "transcript.jsonl",
        "control.tmp",
    }
    recovery.cleanup(pending)

    assert not run.run_directory.exists()
    assert private_sentinel.read_text(encoding="utf-8") == "preserve sibling\n"


def test_empty_directory_after_interrupted_cleanup_is_reloadable_for_final_rmdir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    private_sentinel = private_root / "another-run.keep"
    private_sentinel.write_text("preserve sibling\n", encoding="utf-8")
    adapter, running, _ = _start_mock_run(repository, private_root)
    run = adapter.cancel(running)

    def interrupt_final_rmdir(path: str | Path) -> None:
        raise OSError(f"injected final-directory interruption: {path}")

    with monkeypatch.context() as context:
        context.setattr("second_mate.trusted_local.os.rmdir", interrupt_final_rmdir)
        with pytest.raises(TrustedLocalBoundaryError, match="cannot remove empty"):
            adapter.cleanup(run, recovery_disposition="abandoned")

    assert run.run_directory.is_dir()
    assert tuple(run.run_directory.iterdir()) == ()

    recovery = OfflineTrustedLocalAdapter(LaunchingControlPlane())
    pending = recovery.load(
        basis=_basis(),
        activation_id=run.activation_id,
        repository=repository,
        private_root=private_root,
    )
    assert pending.phase == "cleanup-pending"
    assert pending.artifact_identities == {}
    recovery.cleanup(pending)

    assert not run.run_directory.exists()
    assert (private_root / "activation.run-001.consumed.json").is_file()
    assert private_sentinel.read_text(encoding="utf-8") == "preserve sibling\n"


def test_empty_directory_without_cleanup_authorization_is_not_recovery_evidence(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    _adapter, run, _ = _start_mock_run(repository, private_root)
    for artifact in run.run_directory.iterdir():
        artifact.unlink()

    recovery = OfflineTrustedLocalAdapter(LaunchingControlPlane())
    with pytest.raises(TrustedLocalBoundaryError, match="cleanup authorization"):
        recovery.load(
            basis=_basis(),
            activation_id=run.activation_id,
            repository=repository,
            private_root=private_root,
        )

    assert run.run_directory.is_dir()
    assert tuple(run.run_directory.iterdir()) == ()
    assert (private_root / "activation.run-001.consumed.json").is_file()


def test_empty_replacement_directory_is_not_interrupted_cleanup_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    adapter, running, _ = _start_mock_run(repository, private_root)
    run = adapter.cancel(running)

    def interrupt_final_rmdir(path: str | Path) -> None:
        raise OSError(f"injected interruption: {path}")

    with monkeypatch.context() as context:
        context.setattr(
            "second_mate.trusted_local.os.rmdir",
            interrupt_final_rmdir,
        )
        with pytest.raises(TrustedLocalBoundaryError, match="cannot remove empty"):
            adapter.cleanup(run, recovery_disposition="abandoned")

    marker = trusted_local_module._read_durable_json(
        private_root / "activation.run-001.consumed.json", "test marker"
    )
    assert isinstance(marker, dict)
    recorded_run_identity = (
        marker["cleanup_authorization"]["run_directory"]["device"],
        marker["cleanup_authorization"]["run_directory"]["inode"],
    )
    recorded_root_change_time = marker["cleanup_authorization"]["private_root"]["change_time_ns"]
    run.run_directory.rmdir()
    run.run_directory.mkdir(mode=0o700)
    assert private_root.stat().st_ctime_ns != recorded_root_change_time

    real_directory_identity = trusted_local_module._private_directory_identity

    def report_reused_run_identity(path: Path, label: str) -> tuple[int, int]:
        if path == run.run_directory:
            return recorded_run_identity
        return real_directory_identity(path, label)

    recovery = OfflineTrustedLocalAdapter(LaunchingControlPlane())
    with monkeypatch.context() as context:
        context.setattr(
            "second_mate.trusted_local._private_directory_identity",
            report_reused_run_identity,
        )
        with pytest.raises(TrustedLocalBoundaryError, match="directory identity"):
            recovery.load(
                basis=_basis(),
                activation_id=run.activation_id,
                repository=repository,
                private_root=private_root,
            )

    assert run.run_directory.is_dir()
    assert tuple(run.run_directory.iterdir()) == ()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("unexpected", "unexpected artifact"),
        ("replaced", "identity"),
        ("missing-session", "omits its durable session intent"),
        ("missing-intent", "exactly the recorded artifacts"),
    ],
)
def test_reload_refuses_tampered_interrupted_cleanup_without_deleting_more(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    message: str,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    private_sentinel = private_root / "another-run.keep"
    private_sentinel.write_text("preserve sibling\n", encoding="utf-8")
    adapter, running, _ = _start_mock_run(repository, private_root)
    run = adapter.cancel(running)
    real_unlink = os.unlink

    def interrupt_after_first_unlink(path: str, *, dir_fd: int | None = None) -> None:
        if path == "control.tmp":
            raise OSError("injected interruption after first unlink")
        real_unlink(path, dir_fd=dir_fd)

    with monkeypatch.context() as context:
        context.setattr("second_mate.trusted_local.os.unlink", interrupt_after_first_unlink)
        with pytest.raises(TrustedLocalBoundaryError, match="cannot remove exact"):
            adapter.cleanup(run, recovery_disposition="abandoned")

    session_path = run.run_directory / "session.json"
    control_path = run.run_directory / "control.tmp"
    if mutation == "unexpected":
        (run.run_directory / "unrecorded.txt").write_text("do not guess\n", encoding="utf-8")
    elif mutation == "replaced":
        control_path.unlink()
        control_path.write_text("replacement\n", encoding="utf-8")
        os.chmod(control_path, 0o600)
    elif mutation == "missing-session":
        session_path.unlink()
    else:
        session = trusted_local_module._read_durable_json(session_path, "test session")
        assert isinstance(session, dict)
        session["phase"] = "unknown-running"
        session_path.write_text(json.dumps(session), encoding="utf-8")

    remaining_names = {path.name for path in run.run_directory.iterdir()}
    recovery = OfflineTrustedLocalAdapter(LaunchingControlPlane())
    with pytest.raises(TrustedLocalBoundaryError, match=message):
        recovery.load(
            basis=_basis(),
            activation_id=run.activation_id,
            repository=repository,
            private_root=private_root,
        )

    assert {path.name for path in run.run_directory.iterdir()} == remaining_names
    assert (private_root / "activation.run-001.consumed.json").is_file()
    assert private_sentinel.read_text(encoding="utf-8") == "preserve sibling\n"


def test_cleanup_refuses_an_active_run_and_preserves_every_recovery_artifact(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    adapter, run, _ = _start_mock_run(repository, private_root)

    with pytest.raises(TrustedLocalBoundaryError, match="active trusted-local run"):
        adapter.cleanup(run)

    assert {path.name for path in run.run_directory.iterdir()} == {
        "session.json",
        "transcript.jsonl",
        "control.tmp",
    }


def test_unknown_running_cleanup_requires_an_explicit_abandonment_disposition(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    adapter, started, _ = _start_mock_run(repository, private_root)
    unknown = adapter.cancel(started)

    with pytest.raises(TrustedLocalBoundaryError, match="explicit abandoned disposition"):
        adapter.cleanup(unknown)

    assert unknown.run_directory.is_dir()

    adapter.cleanup(unknown, recovery_disposition="abandoned")

    assert not unknown.run_directory.exists()


def test_unknown_running_cleanup_refuses_while_this_adapter_still_owns_the_process(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    process = FailingOfflineProcess("read")
    adapter = OfflineTrustedLocalAdapter(LaunchingControlPlane(process))
    started = adapter.start(
        basis=_basis(),
        activation_data=_activation(),
        repository=repository,
        private_root=private_root,
    )
    unknown = adapter.finish(started)

    with pytest.raises(TrustedLocalBoundaryError, match="still owns the process"):
        adapter.cleanup(unknown, recovery_disposition="abandoned")

    assert unknown.run_directory.is_dir()

    recovery_adapter = OfflineTrustedLocalAdapter(LaunchingControlPlane())
    recovered = recovery_adapter.load(
        basis=_basis(),
        activation_id=unknown.activation_id,
        repository=repository,
        private_root=private_root,
    )
    recovery_adapter.cleanup(recovered, recovery_disposition="abandoned")

    assert not recovered.run_directory.exists()


def test_cleanup_refuses_unexpected_entry_before_deleting_anything(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    adapter, run, _ = _start_mock_run(repository, private_root)
    run = adapter.cancel(run)
    unexpected = run.run_directory / "unrecorded.txt"
    unexpected.write_text("do not guess\n", encoding="utf-8")

    with pytest.raises(TrustedLocalBoundaryError, match="exactly the recorded artifacts"):
        adapter.cleanup(run, recovery_disposition="abandoned")

    assert {path.name for path in run.run_directory.iterdir()} == {
        "session.json",
        "transcript.jsonl",
        "control.tmp",
        "unrecorded.txt",
    }


def test_cleanup_refuses_replaced_artifact_before_deleting_anything(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    repository_sentinel = repository / "work.txt"
    repository_sentinel.write_text("preserve repository work\n", encoding="utf-8")
    private_root = _private_root(tmp_path / "private")
    adapter, run, _ = _start_mock_run(repository, private_root)
    run = adapter.cancel(run)
    transcript = run.run_directory / "transcript.jsonl"
    transcript.unlink()
    transcript.symlink_to(repository_sentinel)

    with pytest.raises(TrustedLocalBoundaryError, match="identity"):
        adapter.cleanup(run, recovery_disposition="abandoned")

    assert (run.run_directory / "session.json").exists()
    assert (run.run_directory / "control.tmp").exists()
    assert transcript.is_symlink()
    assert repository_sentinel.read_text(encoding="utf-8") == "preserve repository work\n"


def test_cleanup_refuses_session_record_drift_before_deleting_anything(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    adapter, run, _ = _start_mock_run(repository, private_root)
    run = adapter.cancel(run)
    session_path = run.run_directory / "session.json"
    session = json.loads(session_path.read_bytes())
    session["repository"] = "/tmp/not-the-recorded-repository"
    session_path.write_text(json.dumps(session), encoding="utf-8")
    os.chmod(session_path, 0o600)

    with pytest.raises(TrustedLocalBoundaryError, match="session record"):
        adapter.cleanup(run, recovery_disposition="abandoned")

    assert {path.name for path in run.run_directory.iterdir()} == {
        "session.json",
        "transcript.jsonl",
        "control.tmp",
    }


def test_session_write_validates_hard_link_before_truncating_repository_file(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    repository_sentinel = repository / "work.txt"
    repository_sentinel.write_text("preserve repository work\n", encoding="utf-8")
    private_root = _private_root(tmp_path / "private")
    adapter, run, _ = _start_mock_run(repository, private_root)
    session_path = run.run_directory / "session.json"
    session_path.unlink()
    os.link(repository_sentinel, session_path)

    with pytest.raises(TrustedLocalBoundaryError, match="identity"):
        adapter.cancel(run)

    assert repository_sentinel.read_text(encoding="utf-8") == "preserve repository work\n"


def test_completed_jsonl_lifecycle_binds_session_but_requires_independent_evidence(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    session_id = "019fcdda-2c17-7f51-9e81-a56f5b9585dc"
    events = [
        {"type": "thread.started", "thread_id": session_id},
        {"type": "turn.started"},
        {
            "type": "item.completed",
            "item": {
                "type": "file_change",
                "changes": [{"path": "claimed.txt", "kind": "update"}],
            },
        },
        {
            "type": "turn.completed",
            "usage": {"input_tokens": 1_000_000, "output_tokens": 500_000},
        },
    ]
    transcript = b"".join(
        json.dumps(event, separators=(",", ":")).encode("utf-8") + b"\n" for event in events
    )
    process = ScriptedOfflineProcess(
        [transcript[:19], transcript[19:73], transcript[73:]], exit_code=0
    )
    control_plane = LaunchingControlPlane(process)
    adapter = OfflineTrustedLocalAdapter(control_plane)
    started = adapter.start(
        basis=_basis(),
        activation_data=_activation(),
        repository=repository,
        private_root=private_root,
    )

    completed = adapter.finish(started)

    assert completed.phase == "completed"
    assert completed.session_id == session_id
    assert completed.independent_evidence_required is True
    assert (completed.run_directory / "transcript.jsonl").read_bytes() == transcript
    assert (completed.run_directory / "control.tmp").read_bytes() == b""
    session = json.loads((completed.run_directory / "session.json").read_bytes())
    assert session["phase"] == "completed"
    assert session["session_id"] == session_id
    assert session["independent_evidence_required"] is True
    assert "evidence" not in session
    assert "token_limit" not in session


def _event_line(event: dict[str, object]) -> bytes:
    return json.dumps(event, separators=(",", ":")).encode("utf-8") + b"\n"


def _finish_transcript(tmp_path: Path, transcript: bytes, *, exit_code: int = 0) -> TrustedLocalRun:
    repository = tmp_path / "repository"
    repository.mkdir(parents=True)
    private_root = _private_root(tmp_path / "private")
    process = ScriptedOfflineProcess([transcript], exit_code=exit_code)
    adapter = OfflineTrustedLocalAdapter(LaunchingControlPlane(process))
    started = adapter.start(
        basis=_basis(),
        activation_data=_activation(),
        repository=repository,
        private_root=private_root,
    )
    return adapter.finish(started)


@pytest.mark.parametrize(
    "transcript",
    [
        b'{"type":"thread.started","type":"thread.started",'
        b'"thread_id":"019fcdda-2c17-7f51-9e81-a56f5b9585dc"}\n',
        b"not-json\n",
        _event_line({"type": "turn.started"}),
        _event_line(
            {
                "type": "thread.started",
                "thread_id": "019fcdda-2c17-7f51-9e81-a56f5b9585dc",
            }
        )
        + _event_line(
            {
                "type": "thread.started",
                "thread_id": "019fcdda-2c17-7f51-9e81-a56f5b9585dc",
            }
        ),
        _event_line(
            {
                "type": "thread.started",
                "thread_id": "019fcdda-2c17-7f51-9e81-a56f5b9585dc",
            }
        )
        + _event_line({"type": "turn.started"})
        + _event_line({"type": "error", "message": "ambiguous provider error"}),
        _event_line(
            {
                "type": "thread.started",
                "thread_id": "019fcdda-2c17-7f51-9e81-a56f5b9585dc",
            }
        )
        + _event_line({"type": "turn.started"})
        + _event_line({"type": "turn.completed"})
        + _event_line({"type": "item.completed", "item": {"type": "message"}}),
    ],
    ids=[
        "duplicate-json-field",
        "malformed-json",
        "out-of-order",
        "duplicate-session",
        "error-event",
        "event-after-terminal",
    ],
)
def test_ambiguous_jsonl_protocol_fails_to_unknown_running(
    tmp_path: Path, transcript: bytes
) -> None:
    run = _finish_transcript(tmp_path, transcript)

    assert run.phase == "unknown-running"
    assert run.run_directory.exists()


def test_truncated_or_oversized_jsonl_fails_to_unknown_running(tmp_path: Path) -> None:
    session = _event_line(
        {
            "type": "thread.started",
            "thread_id": "019fcdda-2c17-7f51-9e81-a56f5b9585dc",
        }
    )
    turn = _event_line({"type": "turn.started"})
    truncated = session + turn + b'{"type":"turn.completed"}'
    oversized = (
        session
        + turn
        + b'{"type":"item.completed","item":{"text":"'
        + (b"x" * (1024 * 1024))
        + b'"}}\n'
    )

    truncated_run = _finish_transcript(tmp_path / "truncated", truncated)
    oversized_run = _finish_transcript(tmp_path / "oversized", oversized)

    assert truncated_run.phase == "unknown-running"
    assert (truncated_run.run_directory / "control.tmp").read_bytes().endswith(b"}")
    assert oversized_run.phase == "unknown-running"


def test_unterminated_oversized_jsonl_keeps_parser_state_bounded(tmp_path: Path) -> None:
    transcript = b'{"type":"thread.started","padding":"' + (b"x" * (2 * 1024 * 1024))

    run = _finish_transcript(tmp_path, transcript)

    assert run.phase == "unknown-running"
    assert (run.run_directory / "transcript.jsonl").stat().st_size == len(transcript)
    assert (run.run_directory / "control.tmp").stat().st_size <= 1024 * 1024


def test_completed_event_with_nonzero_exit_is_unknown_running(tmp_path: Path) -> None:
    transcript = b"".join(
        (
            _event_line(
                {
                    "type": "thread.started",
                    "thread_id": "019fcdda-2c17-7f51-9e81-a56f5b9585dc",
                }
            ),
            _event_line({"type": "turn.started"}),
            _event_line({"type": "turn.completed"}),
        )
    )

    run = _finish_transcript(tmp_path, transcript, exit_code=17)

    assert run.phase == "unknown-running"


def test_valid_turn_failure_is_a_terminal_failed_run(tmp_path: Path) -> None:
    transcript = b"".join(
        (
            _event_line(
                {
                    "type": "thread.started",
                    "thread_id": "019fcdda-2c17-7f51-9e81-a56f5b9585dc",
                }
            ),
            _event_line({"type": "turn.started"}),
            _event_line({"type": "turn.failed", "error": {"message": "mock failure"}}),
        )
    )

    run = _finish_transcript(tmp_path, transcript, exit_code=1)

    assert run.phase == "failed"
    assert run.independent_evidence_required is True


def test_turn_failure_with_zero_exit_is_unknown_running(tmp_path: Path) -> None:
    transcript = b"".join(
        (
            _event_line(
                {
                    "type": "thread.started",
                    "thread_id": "019fcdda-2c17-7f51-9e81-a56f5b9585dc",
                }
            ),
            _event_line({"type": "turn.started"}),
            _event_line({"type": "turn.failed", "error": {"message": "mock failure"}}),
        )
    )

    run = _finish_transcript(tmp_path, transcript, exit_code=0)

    assert run.phase == "unknown-running"


def test_turn_failure_with_signal_exit_is_unknown_running(tmp_path: Path) -> None:
    transcript = b"".join(
        (
            _event_line(
                {
                    "type": "thread.started",
                    "thread_id": "019fcdda-2c17-7f51-9e81-a56f5b9585dc",
                }
            ),
            _event_line({"type": "turn.started"}),
            _event_line({"type": "turn.failed", "error": {"message": "mock failure"}}),
        )
    )

    run = _finish_transcript(tmp_path, transcript, exit_code=-15)

    assert run.phase == "unknown-running"


@pytest.mark.parametrize("failure", ["read", "wait"])
def test_control_plane_io_failure_is_unknown_running_and_retains_private_state(
    tmp_path: Path, failure: str
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    process = FailingOfflineProcess(failure)
    adapter = OfflineTrustedLocalAdapter(LaunchingControlPlane(process))
    started = adapter.start(
        basis=_basis(),
        activation_data=_activation(),
        repository=repository,
        private_root=private_root,
    )

    run = adapter.finish(started)

    assert run.phase == "unknown-running"
    assert {path.name for path in run.run_directory.iterdir()} == {
        "session.json",
        "transcript.jsonl",
        "control.tmp",
    }


def test_cancel_is_unknown_running_retains_artifacts_and_cannot_implicitly_retry(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    transcript = b"".join(
        (
            _event_line(
                {
                    "type": "thread.started",
                    "thread_id": "019fcdda-2c17-7f51-9e81-a56f5b9585dc",
                }
            ),
            _event_line({"type": "turn.started"}),
            _event_line({"type": "turn.completed"}),
        )
    )
    process = ScriptedOfflineProcess([transcript], exit_code=0)
    adapter = OfflineTrustedLocalAdapter(LaunchingControlPlane(process))
    started = adapter.start(
        basis=_basis(),
        activation_data=_activation(),
        repository=repository,
        private_root=private_root,
    )

    cancelled = adapter.cancel(started)
    retried = adapter.finish(cancelled)

    assert process.cancel_requested is True
    assert process.read_count == 0
    assert process.wait_count == 0
    assert cancelled.phase == "unknown-running"
    assert retried == cancelled
    assert {path.name for path in cancelled.run_directory.iterdir()} == {
        "session.json",
        "transcript.jsonl",
        "control.tmp",
    }
    assert (cancelled.run_directory / "transcript.jsonl").read_bytes() == b""
    session = json.loads((cancelled.run_directory / "session.json").read_bytes())
    assert session["phase"] == "unknown-running"


def test_cleanup_cannot_make_a_cancelled_activation_reusable(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    first_control_plane = LaunchingControlPlane()
    first_adapter = OfflineTrustedLocalAdapter(first_control_plane)
    started = first_adapter.start(
        basis=_basis(),
        activation_data=_activation(),
        repository=repository,
        private_root=private_root,
    )
    cancelled = first_adapter.cancel(started)
    first_adapter.cleanup(cancelled, recovery_disposition="abandoned")
    competing_control_plane = LaunchingControlPlane()

    with pytest.raises(TrustedLocalBoundaryError, match="already consumed"):
        OfflineTrustedLocalAdapter(competing_control_plane).start(
            basis=_basis(),
            activation_data=_activation(),
            repository=repository,
            private_root=private_root,
        )

    assert first_control_plane.launch_count == 1
    assert competing_control_plane.launch_count == 0


def test_ambiguous_launch_is_durable_unknown_running_with_no_automatic_cleanup(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    control_plane = AmbiguousLaunchControlPlane()

    run = OfflineTrustedLocalAdapter(control_plane).start(
        basis=_basis(),
        activation_data=_activation(),
        repository=repository,
        private_root=private_root,
    )

    assert run.phase == "unknown-running"
    assert run.process_id is None
    assert run.process_start_token is None
    assert control_plane.launch_count == 1
    assert {path.name for path in run.run_directory.iterdir()} == {
        "session.json",
        "transcript.jsonl",
        "control.tmp",
    }
    session = json.loads((run.run_directory / "session.json").read_bytes())
    assert session["phase"] == "unknown-running"
    assert session["process"] is None


def test_reload_reconstructs_identities_and_downgrades_unattached_running_process(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    first_adapter = OfflineTrustedLocalAdapter(LaunchingControlPlane())
    started = first_adapter.start(
        basis=_basis(),
        activation_data=_activation(),
        repository=repository,
        private_root=private_root,
    )
    recovery_control_plane = RecordingControlPlane()

    recovered = OfflineTrustedLocalAdapter(recovery_control_plane).load(
        basis=_basis(),
        activation_id="run-001",
        repository=repository,
        private_root=private_root,
    )

    assert recovered.phase == "unknown-running"
    assert recovered.process_id == started.process_id
    assert recovered.process_start_token == started.process_start_token
    assert recovered.artifact_identities == started.artifact_identities
    assert recovery_control_plane.launch_count == 0
    assert json.loads((recovered.run_directory / "session.json").read_bytes())["phase"] == (
        "unknown-running"
    )
