"""Activation-gated Codex CLI process boundary for trusted-local runs."""

from __future__ import annotations

import hashlib
import os
import re
import signal
import stat
import subprocess
import time
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass, replace
from pathlib import Path
from typing import BinaryIO, cast

from second_mate.domain import JsonObject, ValidationError, digest_json
from second_mate.repository import inspect_revision
from second_mate.trusted_local import (
    OfflineLaunchRequest,
    OfflineTrustedLocalAdapter,
    TrustedLocalAuthorityError,
    TrustedLocalBasis,
    TrustedLocalBoundaryError,
    TrustedLocalRun,
)

_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_ENVIRONMENT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_MAX_PROMPT_BYTES = 64 * 1024
_PROBE_TIMEOUT_SECONDS = 5
_READ_CHUNK_BYTES = 64 * 1024
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
    "workspace_dependencies",
)


def _is_digest(value: object) -> bool:
    return isinstance(value, str) and _DIGEST.fullmatch(value) is not None


def _bytes_digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _provider_boundary_document(boundary: CodexCliProviderBoundary) -> JsonObject:
    return {
        "adapter": "codex-cli-trusted-local",
        "argv_policy": {
            "color": "never",
            "disabled_features": list(_DISABLED_FEATURES),
            "ephemeral": True,
            "ignore_rules": True,
            "ignore_user_config": True,
            "mcp_servers": "empty",
            "mode": "trusted-local-unsandboxed",
            "prompt_source": "stdin",
            "stream": "jsonl",
            "strict_config": True,
        },
        "cancellation": {
            "interrupt_timeout_ms": boundary.interrupt_timeout_ms,
            "terminate_timeout_ms": boundary.terminate_timeout_ms,
        },
        "environment_value_sha256": [
            {"name": name, "sha256": digest} for name, digest in boundary.environment_value_sha256
        ],
        "executable": str(boundary.executable),
        "executable_sha256": boundary.executable_sha256,
        "exec_help_sha256": boundary.exec_help_sha256,
        "model": boundary.model,
        "prompt_sha256": boundary.prompt_sha256,
        "schema_version": 2,
        "target_root": str(boundary.target_root),
        "version_output": boundary.version_output,
    }


@dataclass(frozen=True, slots=True)
class CodexCliProviderBoundary:
    """Immutable inputs whose digest must match one trusted-local activation."""

    executable: Path
    target_root: Path
    executable_sha256: str
    version_output: str
    exec_help_sha256: str
    model: str
    prompt_sha256: str
    environment_value_sha256: tuple[tuple[str, str], ...]
    interrupt_timeout_ms: int
    terminate_timeout_ms: int

    def __post_init__(self) -> None:
        if not isinstance(self.executable, Path) or not self.executable.is_absolute():
            raise TrustedLocalBoundaryError(
                "Codex CLI executable must be an absolute unaliased path"
            )
        if not isinstance(self.target_root, Path) or not self.target_root.is_absolute():
            raise TrustedLocalBoundaryError(
                "Codex CLI target root must be an absolute unaliased path"
            )
        for label, digest_value in (
            ("executable", self.executable_sha256),
            ("exec help", self.exec_help_sha256),
            ("prompt", self.prompt_sha256),
        ):
            if not _is_digest(digest_value):
                raise TrustedLocalBoundaryError(
                    f"Codex CLI {label} digest must be lowercase SHA-256"
                )
        if (
            not isinstance(self.version_output, str)
            or not self.version_output
            or "\n" in self.version_output
            or "\r" in self.version_output
            or len(self.version_output.encode("utf-8")) > 256
        ):
            raise TrustedLocalBoundaryError(
                "Codex CLI version output must be one bounded non-empty line"
            )
        if (
            not isinstance(self.model, str)
            or not self.model.strip()
            or any(character in self.model for character in ("\0", "\n", "\r"))
        ):
            raise TrustedLocalBoundaryError("Codex CLI model must be exact non-empty text")
        if type(self.environment_value_sha256) is not tuple:
            raise TrustedLocalBoundaryError(
                "Codex CLI environment bindings must be an immutable sorted tuple"
            )
        names: list[str] = []
        for item in self.environment_value_sha256:
            if type(item) is not tuple or len(item) != 2:
                raise TrustedLocalBoundaryError(
                    "Codex CLI environment bindings must contain name/digest pairs"
                )
            name, digest = item
            if not isinstance(name, str) or _ENVIRONMENT_NAME.fullmatch(name) is None:
                raise TrustedLocalBoundaryError("Codex CLI environment name is invalid")
            if not _is_digest(digest):
                raise TrustedLocalBoundaryError(
                    "Codex CLI environment digest must be lowercase SHA-256"
                )
            names.append(name)
        if not names or names != sorted(set(names)):
            raise TrustedLocalBoundaryError(
                "Codex CLI environment bindings must be non-empty, unique, and sorted"
            )
        for label, timeout_value in (
            ("interrupt", self.interrupt_timeout_ms),
            ("terminate", self.terminate_timeout_ms),
        ):
            if type(timeout_value) is not int or not 1 <= timeout_value <= 60_000:
                raise TrustedLocalBoundaryError(
                    f"Codex CLI {label} timeout must be 1..60000 milliseconds"
                )

    def digest(self) -> str:
        """Return the exact digest stored in ``TrustedLocalBasis``."""

        return digest_json(_provider_boundary_document(self))


def _real_executable(path: Path) -> Path:
    try:
        entry = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise TrustedLocalBoundaryError(f"cannot inspect Codex CLI executable: {error}") from error
    if (
        not stat.S_ISREG(entry.st_mode)
        or Path(os.path.abspath(path)) != resolved
        or entry.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        or not os.access(resolved, os.X_OK)
    ):
        raise TrustedLocalBoundaryError(
            "Codex CLI executable must be an unaliased executable regular file without "
            "group/world write access"
        )
    return resolved


def _open_verified_executable(path: Path, expected_digest: str) -> tuple[Path, int]:
    resolved = _real_executable(path)
    descriptor: int | None = None
    try:
        descriptor = os.open(resolved, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        metadata = os.fstat(descriptor)
        entry = resolved.lstat()
        if not stat.S_ISREG(metadata.st_mode) or (metadata.st_dev, metadata.st_ino) != (
            entry.st_dev,
            entry.st_ino,
        ):
            raise OSError("executable identity changed")
        digest = hashlib.sha256()
        while chunk := os.read(descriptor, _READ_CHUNK_BYTES):
            digest.update(chunk)
        if digest.hexdigest() != expected_digest:
            raise OSError("executable digest changed")
        os.lseek(descriptor, 0, os.SEEK_SET)
        result = descriptor
        descriptor = None
        return resolved, result
    except OSError as error:
        raise TrustedLocalBoundaryError(f"Codex CLI executable digest changed: {error}") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _run_probe(
    argv: list[str],
    *,
    executable_descriptor: int,
    repository: Path,
    environment: Mapping[str, str],
    label: str,
) -> bytes:
    try:
        result = subprocess.run(
            argv,
            executable=f"/proc/self/fd/{executable_descriptor}",
            cwd=repository,
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            pass_fds=(executable_descriptor,),
            timeout=_PROBE_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise TrustedLocalBoundaryError(f"Codex CLI {label} probe failed: {error}") from error
    if result.returncode != 0 or result.stderr:
        raise TrustedLocalBoundaryError(f"Codex CLI {label} probe must exit zero without stderr")
    return result.stdout


def _open_identified_control(path: Path, identity: tuple[int, int]) -> int:
    descriptor: int | None = None
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
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
            raise OSError("control artifact identity is unsafe")
        return descriptor
    except OSError as error:
        if descriptor is not None:
            os.close(descriptor)
        raise TrustedLocalBoundaryError(
            f"cannot open exact private control artifact: {error}"
        ) from error


def _linux_process_start_token(process_id: int) -> str:
    try:
        boot_id = Path("/proc/sys/kernel/random/boot_id").read_text(encoding="ascii").strip()
        process_stat = Path(f"/proc/{process_id}/stat").read_text(encoding="ascii")
    except OSError as error:
        raise TrustedLocalBoundaryError(f"cannot bind Linux process identity: {error}") from error
    closing_parenthesis = process_stat.rfind(")")
    fields_after_name = process_stat[closing_parenthesis + 2 :].split()
    if closing_parenthesis < 1 or len(fields_after_name) <= 19 or not boot_id:
        raise TrustedLocalBoundaryError("Linux process identity record is malformed")
    start_ticks = fields_after_name[19]
    if not start_ticks.isdecimal():
        raise TrustedLocalBoundaryError("Linux process start token is malformed")
    return f"linux-proc-v1:{boot_id}:{start_ticks}"


def _process_group_exists(process_group_id: int) -> bool:
    try:
        os.killpg(process_group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError as error:
        raise TrustedLocalBoundaryError(
            "cannot verify the owned Codex CLI process group"
        ) from error
    return True


class _CodexCliProcess:
    manages_control_output = True

    def __init__(
        self,
        process: subprocess.Popen[bytes],
        *,
        interrupt_timeout_ms: int,
        terminate_timeout_ms: int,
    ) -> None:
        if process.stdout is None:
            raise TrustedLocalBoundaryError("Codex CLI stdout pipe is unavailable")
        if os.getpgid(process.pid) != process.pid:
            raise TrustedLocalBoundaryError("Codex CLI process does not own its process group")
        self._process = process
        self._stdout = cast(BinaryIO, process.stdout)
        self._interrupt_timeout_ms = interrupt_timeout_ms
        self._terminate_timeout_ms = terminate_timeout_ms
        self._nonblocking_after_cancel = False
        self.pid = process.pid
        self.start_token = _linux_process_start_token(process.pid)

    def read_chunk(self) -> bytes | None:
        try:
            chunk = os.read(self._stdout.fileno(), _READ_CHUNK_BYTES)
        except BlockingIOError:
            if self._nonblocking_after_cancel:
                return None
            raise
        return chunk or None

    def wait(self) -> int:
        exit_code = self._process.wait()
        self._stdout.close()
        return exit_code

    def prepare_cancel_drain(self) -> bool:
        """Make already-buffered output safe to drain without blocking."""

        if self._process.poll() is None:
            return False
        try:
            os.set_blocking(self._stdout.fileno(), False)
        except (OSError, ValueError):
            with suppress(OSError, ValueError):
                self._stdout.close()
            return False
        self._nonblocking_after_cancel = True
        return True

    def _wait_for_group(self, timeout_ms: int) -> bool:
        deadline = time.monotonic() + (timeout_ms / 1000)
        while time.monotonic() < deadline:
            self._process.poll()
            if not _process_group_exists(self.pid):
                return True
            time.sleep(min(0.01, timeout_ms / 1000))
        self._process.poll()
        return not _process_group_exists(self.pid)

    def request_cancel(self) -> None:
        if _linux_process_start_token(self.pid) != self.start_token:
            raise TrustedLocalBoundaryError("Codex CLI process identity changed before cancel")
        for cancel_signal, timeout_ms in (
            (signal.SIGINT, self._interrupt_timeout_ms),
            (signal.SIGTERM, self._terminate_timeout_ms),
            (signal.SIGKILL, self._terminate_timeout_ms),
        ):
            try:
                os.killpg(self.pid, cancel_signal)
            except ProcessLookupError:
                self._process.poll()
                return
            if self._wait_for_group(timeout_ms):
                self._process.poll()
                return
        self._process.poll()
        if _process_group_exists(self.pid):
            raise TrustedLocalBoundaryError(
                "Codex CLI process group remains ambiguous after forced cancellation"
            )


def _stop_unqualified_process(process: subprocess.Popen[bytes]) -> None:
    with suppress(OSError):
        if os.getpgid(process.pid) == process.pid:
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    with suppress(subprocess.TimeoutExpired):
        process.wait(timeout=1)
    for stream in (process.stdin, process.stdout):
        if stream is not None:
            with suppress(OSError):
                stream.close()


class _CodexCliControlPlane:
    offline = False

    def __init__(
        self,
        *,
        boundary: CodexCliProviderBoundary,
        environment: Mapping[str, str],
        prompt: bytes,
    ) -> None:
        self.boundary = boundary
        self.provider_boundary_digest = boundary.digest()
        self._environment = dict(environment)
        self._prompt = prompt
        self._qualified_repository: Path | None = None
        self._launched = False
        self._validate_runtime_values()

    def _validate_runtime_values(self) -> None:
        if not isinstance(self._prompt, bytes) or not self._prompt:
            raise TrustedLocalBoundaryError("Codex CLI prompt must be non-empty bytes")
        if len(self._prompt) > _MAX_PROMPT_BYTES:
            raise TrustedLocalBoundaryError("Codex CLI prompt exceeds the 64 KiB launch bound")
        if _bytes_digest(self._prompt) != self.boundary.prompt_sha256:
            raise TrustedLocalBoundaryError("Codex CLI prompt does not match its boundary digest")
        runtime_names = sorted(self._environment)
        boundary_names = [name for name, _ in self.boundary.environment_value_sha256]
        if runtime_names != boundary_names:
            raise TrustedLocalBoundaryError(
                "Codex CLI environment names do not match the exact boundary"
            )
        expected_digests = dict(self.boundary.environment_value_sha256)
        for name, value in self._environment.items():
            if (
                not isinstance(name, str)
                or not isinstance(value, str)
                or "\0" in name
                or "\0" in value
                or _bytes_digest(value.encode("utf-8")) != expected_digests[name]
            ):
                raise TrustedLocalBoundaryError(
                    "Codex CLI environment value does not match its boundary digest"
                )

    def qualify(self, repository: Path) -> None:
        target_config = repository / ".codex" / "config.toml"
        if os.path.lexists(target_config):
            raise TrustedLocalBoundaryError(
                "target Codex configuration must be absent for this reduced-capability boundary"
            )
        executable, executable_descriptor = _open_verified_executable(
            self.boundary.executable, self.boundary.executable_sha256
        )
        try:
            version = _run_probe(
                [str(executable), "--version"],
                executable_descriptor=executable_descriptor,
                repository=repository,
                environment=self._environment,
                label="version",
            )
            expected_version = (self.boundary.version_output + "\n").encode("utf-8")
            if version != expected_version:
                raise TrustedLocalBoundaryError("Codex CLI version output changed")
            exec_help = _run_probe(
                [str(executable), "exec", "--help"],
                executable_descriptor=executable_descriptor,
                repository=repository,
                environment=self._environment,
                label="exec help",
            )
            if _bytes_digest(exec_help) != self.boundary.exec_help_sha256:
                raise TrustedLocalBoundaryError("Codex CLI exec help output changed")
        finally:
            os.close(executable_descriptor)
        self._qualified_repository = repository

    def _argv(self, repository: Path) -> list[str]:
        result = [
            str(self.boundary.executable),
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
        result.extend(("--model", self.boundary.model, "--cd", str(repository), "-"))
        return result

    def launch(self, request: OfflineLaunchRequest) -> _CodexCliProcess:
        if self._qualified_repository != request.repository:
            raise TrustedLocalBoundaryError("Codex CLI launch repository was not exactly qualified")
        if self._launched:
            raise TrustedLocalBoundaryError("Codex CLI control plane is one-shot")
        if (
            request.control_path.parent != request.transcript_path.parent
            or request.control_path.name != "control.tmp"
            or request.transcript_path.name != "transcript.jsonl"
        ):
            raise TrustedLocalBoundaryError("Codex CLI private launch paths are not exact")
        self._launched = True
        _, executable_descriptor = _open_verified_executable(
            self.boundary.executable, self.boundary.executable_sha256
        )
        try:
            control_descriptor = _open_identified_control(
                request.control_path, request.control_identity
            )
        except Exception:
            os.close(executable_descriptor)
            raise
        process: subprocess.Popen[bytes] | None = None
        try:
            process = subprocess.Popen(
                self._argv(request.repository),
                executable=f"/proc/self/fd/{executable_descriptor}",
                cwd=request.repository,
                env=self._environment,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=control_descriptor,
                bufsize=0,
                close_fds=True,
                pass_fds=(executable_descriptor,),
                start_new_session=True,
            )
        except OSError as error:
            raise TrustedLocalBoundaryError(f"cannot launch Codex CLI process: {error}") from error
        finally:
            os.close(control_descriptor)
            os.close(executable_descriptor)
        try:
            live_process = _CodexCliProcess(
                process,
                interrupt_timeout_ms=self.boundary.interrupt_timeout_ms,
                terminate_timeout_ms=self.boundary.terminate_timeout_ms,
            )
            if process.stdin is None:
                raise TrustedLocalBoundaryError("Codex CLI stdin pipe is unavailable")
            remaining = memoryview(self._prompt)
            while remaining:
                written = process.stdin.write(remaining)
                if written is None or written <= 0:
                    raise BrokenPipeError("short prompt write")
                remaining = remaining[written:]
            process.stdin.flush()
            process.stdin.close()
            return live_process
        except Exception:
            _stop_unqualified_process(process)
            raise


class CodexCliTrustedLocalAdapter(OfflineTrustedLocalAdapter):
    """Activation-gated Codex CLI adapter with no user-facing dispatch command."""

    def __init__(
        self,
        *,
        boundary: CodexCliProviderBoundary,
        environment: Mapping[str, str],
        prompt: bytes,
    ) -> None:
        self._codex_control_plane = _CodexCliControlPlane(
            boundary=boundary,
            environment=environment,
            prompt=prompt,
        )
        super().__init__(self._codex_control_plane)

    @property
    def provider_boundary_digest(self) -> str:
        return self._codex_control_plane.provider_boundary_digest

    def _validate_control_plane(self, *, basis: TrustedLocalBasis, repository: Path) -> None:
        if self._codex_control_plane.offline is not False:
            raise TrustedLocalBoundaryError(
                "Codex CLI adapter requires an explicitly live control plane"
            )
        if basis.provider_boundary_digest != self.provider_boundary_digest:
            raise TrustedLocalAuthorityError(
                "Codex CLI provider boundary does not match the frozen basis"
            )
        if repository != self._codex_control_plane.boundary.target_root:
            raise TrustedLocalBoundaryError("Codex CLI target root changed")
        try:
            revision = inspect_revision(repository)
        except ValidationError as error:
            raise TrustedLocalBoundaryError(
                f"cannot inspect Codex CLI target revision: {error}"
            ) from error
        if revision.head != basis.target_head:
            raise TrustedLocalBoundaryError("Codex CLI target head changed")
        if revision.fingerprint != basis.target_fingerprint:
            raise TrustedLocalBoundaryError("Codex CLI target fingerprint changed")
        self._codex_control_plane.qualify(repository)

    def cancel(self, run: TrustedLocalRun) -> TrustedLocalRun:
        """Cancel one owned group, then retain every immediately available stream byte."""

        if run.phase not in {"running", "unknown-running"}:
            return run
        process = self._processes.get(run.activation_id)
        if (
            not isinstance(process, _CodexCliProcess)
            or process.pid != run.process_id
            or process.start_token != run.process_start_token
        ):
            self._processes.pop(run.activation_id, None)
            unknown = replace(run, phase="unknown-running")
            self._persist(unknown)
            return unknown
        try:
            process.request_cancel()
        except Exception:
            unknown = replace(run, phase="unknown-running")
            self._persist(unknown)
            return unknown
        if process.prepare_cancel_drain():
            drain_source = replace(run, phase="running")
            drained = self.finish(drain_source)
            unknown = replace(drained, phase="unknown-running")
        else:
            unknown = replace(run, phase="unknown-running")
        self._processes.pop(run.activation_id, None)
        self._persist(unknown)
        return unknown


__all__ = ["CodexCliProviderBoundary", "CodexCliTrustedLocalAdapter"]
