from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import replace
from pathlib import Path

import pytest

from second_mate.trusted_local import (
    TrustedLocalAuthorityError,
    TrustedLocalBasis,
    TrustedLocalBoundaryError,
)
from second_mate.trusted_local_codex import (
    CodexCliProviderBoundary,
    CodexCliTrustedLocalAdapter,
)

_SESSION_ID = "12345678-1234-5678-9234-567812345678"
_VERSION = "fake-codex 0.146.0"
_EXEC_HELP = b"fake codex exec help\n"
_PROMPT = b"Audit only the exact approved packet.\n"
_DISABLED_FEATURES = (
    "apps",
    "browser_use",
    "browser_use_external",
    "browser_use_full_cdp_access",
    "computer_use",
    "hooks",
    "image_generation",
    "in_app_browser",
    "multi_agent",
    "multi_agent_v2",
    "plugins",
    "remote_plugin",
    "skill_search",
    "skill_mcp_dependency_install",
    "standalone_web_search",
    "web_search_request",
    "workspace_dependencies",
)


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256(path.read_bytes())


def _private_root(path: Path) -> Path:
    path.mkdir(mode=0o700)
    os.chmod(path, 0o700)
    return path


def _write_fake_codex(path: Path) -> Path:
    path.write_text(
        """#!/usr/bin/python3
import json
import os
import signal
import subprocess
import sys
import time

if sys.argv[1:] == ["--version"]:
    with open(os.environ["SM_FAKE_PROBES"], "ab") as stream:
        stream.write(b"version\\n")
    print("fake-codex 0.146.0")
    raise SystemExit(0)
if sys.argv[1:] == ["exec", "--help"]:
    with open(os.environ["SM_FAKE_PROBES"], "ab") as stream:
        stream.write(b"exec-help\\n")
    sys.stdout.buffer.write(b"fake codex exec help\\n")
    replacement = os.environ.get("SM_FAKE_REPLACEMENT")
    if replacement:
        os.replace(replacement, os.environ["SM_FAKE_EXECUTABLE"])
    raise SystemExit(0)

prompt = sys.stdin.buffer.read()
mode = os.environ["SM_FAKE_MODE"]
launches = os.environ["SM_FAKE_LAUNCHES"]
record = {
    "argv": sys.argv[1:],
    "environment": dict(sorted(os.environ.items())),
    "prompt_hex": prompt.hex(),
}
with open(os.environ["SM_FAKE_RECORD"], "w", encoding="utf-8") as stream:
    json.dump(record, stream, sort_keys=True)
with open(launches, "ab") as stream:
    stream.write(b"launch\\n")

sys.stderr.write("fake private control warning\\n")
sys.stderr.flush()
sys.stdout.write('{"type":"thread.started","thread_id":"12345678-1234-5678-')
sys.stdout.flush()
time.sleep(0.02)
sys.stdout.write('9234-567812345678"}\\n{"type":"turn.started"}\\n')
sys.stdout.flush()

if mode == "complete":
    sys.stdout.write('{"type":"turn.completed"}\\n')
    sys.stdout.flush()
    raise SystemExit(0)
if mode == "cancel":
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    child = subprocess.Popen(
        [
            "/usr/bin/python3",
            "-c",
            "import signal,time; signal.signal(signal.SIGINT, signal.SIG_IGN); "
            "signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)",
        ]
    )
    with open(os.environ["SM_FAKE_READY"], "w", encoding="utf-8") as stream:
        json.dump({"child_pid": child.pid, "parent_pid": os.getpid()}, stream)
    while True:
        time.sleep(1)
raise SystemExit(9)
""",
        encoding="utf-8",
    )
    path.chmod(0o700)
    return path


def _environment(tmp_path: Path, *, mode: str = "complete") -> dict[str, str]:
    return {
        "LC_CTYPE": "C.UTF-8",
        "SM_FAKE_EXECUTABLE": str(tmp_path / "fake-codex"),
        "SM_FAKE_LAUNCHES": str(tmp_path / "launches.log"),
        "SM_FAKE_MODE": mode,
        "SM_FAKE_PROBES": str(tmp_path / "probes.log"),
        "SM_FAKE_READY": str(tmp_path / "ready.json"),
        "SM_FAKE_RECORD": str(tmp_path / "record.json"),
    }


def _boundary(
    executable: Path,
    environment: dict[str, str],
    *,
    executable_sha256: str | None = None,
    version_output: str = _VERSION,
    exec_help_sha256: str = _sha256(_EXEC_HELP),
) -> CodexCliProviderBoundary:
    return CodexCliProviderBoundary(
        executable=executable,
        executable_sha256=executable_sha256 or _file_sha256(executable),
        version_output=version_output,
        exec_help_sha256=exec_help_sha256,
        model="fake-model",
        prompt_sha256=_sha256(_PROMPT),
        environment_value_sha256=tuple(
            (name, _sha256(value.encode("utf-8"))) for name, value in sorted(environment.items())
        ),
        interrupt_timeout_ms=30,
        terminate_timeout_ms=30,
    )


def _basis(provider_boundary_digest: str) -> TrustedLocalBasis:
    return TrustedLocalBasis(
        direction_digest="d" * 64,
        packet_digest="a" * 64,
        preflight_digest="b" * 64,
        repository_id="repository-1",
        target_head="1" * 40,
        target_fingerprint="c" * 64,
        owner_id="owner-1",
        provider_boundary_digest=provider_boundary_digest,
    )


def _activation(basis: TrustedLocalBasis, *, activation_id: str = "live-run-001") -> object:
    return {
        "schema_version": 1,
        "id": activation_id,
        "mode": "trusted-local-unsandboxed",
        "granted_by": "human-operator",
        "granted_at": "2026-08-05T01:00:00Z",
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


def _expected_argv(repository: Path) -> list[str]:
    result = [
        "exec",
        "--strict-config",
        "--json",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--dangerously-bypass-approvals-and-sandbox",
        "--color",
        "never",
        "-c",
        "mcp_servers={}",
    ]
    for feature in _DISABLED_FEATURES:
        result.extend(("--disable", feature))
    result.extend(("--model", "fake-model", "--cd", str(repository), "-"))
    return result


def _process_is_running(process_id: int) -> bool:
    try:
        state = Path(f"/proc/{process_id}/stat").read_text(encoding="utf-8").rsplit(")", 1)[1]
    except FileNotFoundError:
        return False
    return state.split()[0] != "Z"


def test_provider_boundary_mismatch_refuses_before_probe_state_or_launch(tmp_path: Path) -> None:
    executable = _write_fake_codex(tmp_path / "fake-codex")
    environment = _environment(tmp_path)
    boundary = _boundary(executable, environment)
    basis = _basis("f" * 64)
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")

    with pytest.raises(TrustedLocalAuthorityError, match="provider boundary"):
        CodexCliTrustedLocalAdapter(
            boundary=boundary, environment=environment, prompt=_PROMPT
        ).start(
            basis=basis,
            activation_data=_activation(basis),
            repository=repository,
            private_root=private_root,
        )

    assert tuple(private_root.iterdir()) == ()
    assert not (tmp_path / "launches.log").exists()


@pytest.mark.parametrize(
    ("boundary_change", "message"),
    (
        ({"executable_sha256": "0" * 64}, "executable digest"),
        ({"version_output": "fake-codex 9.9.9"}, "version"),
        ({"exec_help_sha256": "1" * 64}, "exec help"),
    ),
)
def test_binary_or_probe_drift_refuses_before_activation_consumption(
    tmp_path: Path, boundary_change: dict[str, str], message: str
) -> None:
    executable = _write_fake_codex(tmp_path / "fake-codex")
    environment = _environment(tmp_path)
    boundary = replace(_boundary(executable, environment), **boundary_change)
    basis = _basis(boundary.digest())
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")

    with pytest.raises(TrustedLocalBoundaryError, match=message):
        CodexCliTrustedLocalAdapter(
            boundary=boundary, environment=environment, prompt=_PROMPT
        ).start(
            basis=basis,
            activation_data=_activation(basis),
            repository=repository,
            private_root=private_root,
        )

    assert tuple(private_root.iterdir()) == ()
    assert not (tmp_path / "launches.log").exists()


@pytest.mark.parametrize("drift", ("prompt", "environment"))
def test_runtime_prompt_or_environment_drift_refuses_before_any_probe(
    tmp_path: Path, drift: str
) -> None:
    executable = _write_fake_codex(tmp_path / "fake-codex")
    environment = _environment(tmp_path)
    boundary = _boundary(executable, environment)

    if drift == "prompt":
        prompt = b"different prompt"
        runtime_environment = environment
    else:
        prompt = _PROMPT
        runtime_environment = {**environment, "SM_FAKE_MODE": "cancel"}

    with pytest.raises(TrustedLocalBoundaryError, match=drift):
        CodexCliTrustedLocalAdapter(
            boundary=boundary,
            environment=runtime_environment,
            prompt=prompt,
        )

    assert not (tmp_path / "launches.log").exists()


def test_target_codex_config_refuses_before_activation_consumption(tmp_path: Path) -> None:
    executable = _write_fake_codex(tmp_path / "fake-codex")
    environment = _environment(tmp_path)
    boundary = _boundary(executable, environment)
    basis = _basis(boundary.digest())
    repository = tmp_path / "repository"
    (repository / ".codex").mkdir(parents=True)
    (repository / ".codex" / "config.toml").write_text("[hooks]\n", encoding="utf-8")
    private_root = _private_root(tmp_path / "private")

    with pytest.raises(TrustedLocalBoundaryError, match="target Codex configuration"):
        CodexCliTrustedLocalAdapter(
            boundary=boundary, environment=environment, prompt=_PROMPT
        ).start(
            basis=basis,
            activation_data=_activation(basis),
            repository=repository,
            private_root=private_root,
        )

    assert tuple(private_root.iterdir()) == ()
    assert not (tmp_path / "launches.log").exists()


def test_unsafe_private_root_refuses_before_executable_probe(tmp_path: Path) -> None:
    executable = _write_fake_codex(tmp_path / "fake-codex")
    environment = _environment(tmp_path)
    boundary = _boundary(executable, environment)
    basis = _basis(boundary.digest())
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = tmp_path / "private"
    private_root.mkdir(mode=0o755)
    os.chmod(private_root, 0o755)

    with pytest.raises(TrustedLocalBoundaryError, match="mode 0700"):
        CodexCliTrustedLocalAdapter(
            boundary=boundary, environment=environment, prompt=_PROMPT
        ).start(
            basis=basis,
            activation_data=_activation(basis),
            repository=repository,
            private_root=private_root,
        )

    assert not (tmp_path / "probes.log").exists()
    assert not (tmp_path / "launches.log").exists()


def test_executable_replacement_after_probe_is_not_launched(tmp_path: Path) -> None:
    executable = _write_fake_codex(tmp_path / "fake-codex")
    replacement = tmp_path / "replacement-codex"
    replacement.write_text(
        """#!/usr/bin/python3
import os
with open(os.environ["SM_FAKE_LAUNCHES"], "ab") as stream:
    stream.write(b"replacement-launch\\n")
""",
        encoding="utf-8",
    )
    replacement.chmod(0o700)
    environment = {
        **_environment(tmp_path),
        "SM_FAKE_REPLACEMENT": str(replacement),
    }
    boundary = _boundary(executable, environment)
    basis = _basis(boundary.digest())
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")

    run = CodexCliTrustedLocalAdapter(
        boundary=boundary, environment=environment, prompt=_PROMPT
    ).start(
        basis=basis,
        activation_data=_activation(basis),
        repository=repository,
        private_root=private_root,
    )

    assert run.phase == "unknown-running"
    assert not (tmp_path / "launches.log").exists()


def test_fake_codex_process_proves_exact_launch_stream_and_private_control(
    tmp_path: Path,
) -> None:
    executable = _write_fake_codex(tmp_path / "fake-codex")
    environment = _environment(tmp_path)
    boundary = _boundary(executable, environment)
    basis = _basis(boundary.digest())
    repository = tmp_path / "repository"
    repository.mkdir()
    repository_sentinel = repository / "sentinel.txt"
    repository_sentinel.write_text("preserve repository work\n", encoding="utf-8")
    private_root = _private_root(tmp_path / "private")
    private_sentinel = private_root / "preserve.txt"
    private_sentinel.write_text("unrelated private data\n", encoding="utf-8")
    private_sentinel.chmod(0o600)
    adapter = CodexCliTrustedLocalAdapter(
        boundary=boundary, environment=environment, prompt=_PROMPT
    )

    run = adapter.start(
        basis=basis,
        activation_data=_activation(basis),
        repository=repository,
        private_root=private_root,
    )
    completed = adapter.finish(run)

    assert completed.phase == "completed"
    assert completed.session_id == _SESSION_ID
    assert completed.independent_evidence_required is True
    expected_transcript = (
        b'{"type":"thread.started","thread_id":"12345678-1234-5678-9234-567812345678"}\n'
        b'{"type":"turn.started"}\n'
        b'{"type":"turn.completed"}\n'
    )
    assert (completed.run_directory / "transcript.jsonl").read_bytes() == expected_transcript
    assert (completed.run_directory / "control.tmp").read_bytes() == (
        b"fake private control warning\n"
    )
    record = json.loads((tmp_path / "record.json").read_text(encoding="utf-8"))
    assert record == {
        "argv": _expected_argv(repository.resolve(strict=True)),
        "environment": dict(sorted(environment.items())),
        "prompt_hex": _PROMPT.hex(),
    }
    assert (tmp_path / "launches.log").read_bytes() == b"launch\n"

    adapter.cleanup(completed)

    assert not completed.run_directory.exists()
    assert repository_sentinel.read_text(encoding="utf-8") == "preserve repository work\n"
    assert private_sentinel.read_text(encoding="utf-8") == "unrelated private data\n"
    assert (private_root / "activation.live-run-001.consumed.json").is_file()


def test_consumed_activation_cannot_launch_the_fake_process_twice(tmp_path: Path) -> None:
    executable = _write_fake_codex(tmp_path / "fake-codex")
    environment = _environment(tmp_path)
    boundary = _boundary(executable, environment)
    basis = _basis(boundary.digest())
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    adapter = CodexCliTrustedLocalAdapter(
        boundary=boundary, environment=environment, prompt=_PROMPT
    )
    first = adapter.start(
        basis=basis,
        activation_data=_activation(basis),
        repository=repository,
        private_root=private_root,
    )
    completed = adapter.finish(first)
    adapter.cleanup(completed)

    with pytest.raises(TrustedLocalBoundaryError, match="already consumed"):
        CodexCliTrustedLocalAdapter(
            boundary=boundary, environment=environment, prompt=_PROMPT
        ).start(
            basis=basis,
            activation_data=_activation(basis),
            repository=repository,
            private_root=private_root,
        )

    assert (tmp_path / "launches.log").read_bytes() == b"launch\n"


def test_owned_process_group_cancellation_is_unknown_running_and_not_reattached(
    tmp_path: Path,
) -> None:
    executable = _write_fake_codex(tmp_path / "fake-codex")
    environment = _environment(tmp_path, mode="cancel")
    boundary = _boundary(executable, environment)
    basis = _basis(boundary.digest())
    repository = tmp_path / "repository"
    repository.mkdir()
    private_root = _private_root(tmp_path / "private")
    adapter = CodexCliTrustedLocalAdapter(
        boundary=boundary, environment=environment, prompt=_PROMPT
    )
    run = adapter.start(
        basis=basis,
        activation_data=_activation(basis),
        repository=repository,
        private_root=private_root,
    )
    deadline = time.monotonic() + 3
    while not (tmp_path / "ready.json").exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    identities = json.loads((tmp_path / "ready.json").read_text(encoding="utf-8"))

    cancelled = adapter.cancel(run)

    assert cancelled.phase == "unknown-running"
    assert cancelled.session_id == _SESSION_ID
    assert (cancelled.run_directory / "transcript.jsonl").read_bytes() == (
        b'{"type":"thread.started","thread_id":"12345678-1234-5678-9234-567812345678"}\n'
        b'{"type":"turn.started"}\n'
    )
    assert (cancelled.run_directory / "control.tmp").read_bytes() == (
        b"fake private control warning\n"
    )
    deadline = time.monotonic() + 3
    while (
        any(_process_is_running(identities[name]) for name in identities)
        and time.monotonic() < deadline
    ):
        time.sleep(0.01)
    assert not _process_is_running(identities["parent_pid"])
    assert not _process_is_running(identities["child_pid"])

    recovered = CodexCliTrustedLocalAdapter(
        boundary=boundary, environment=environment, prompt=_PROMPT
    ).load(
        basis=basis,
        activation_id=cancelled.activation_id,
        repository=repository,
        private_root=private_root,
    )

    assert recovered.phase == "unknown-running"
    assert recovered.process_id == cancelled.process_id
    assert recovered.process_start_token == cancelled.process_start_token
    assert (tmp_path / "launches.log").read_bytes() == b"launch\n"
