"""Authority-guarded dispatch for one FS-01 run."""

from __future__ import annotations

import fcntl
import hashlib
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Never, Protocol, cast

from second_mate.domain import (
    Draft,
    JsonObject,
    JsonValue,
    ValidationError,
    digest_json,
    draft_from_json,
)
from second_mate.repository import (
    FileFact,
    PreflightEnvelope,
    TargetRevision,
    git_private_path,
    inspect_instructions,
    inspect_revision,
    preflight_from_json,
)
from second_mate.store import FileStateStore


class AuthorityError(RuntimeError):
    """Execution authority is missing, stale, or does not match the frozen basis."""


class RunConflictError(RuntimeError):
    """Another durable owner already holds this packet's mutation boundary."""


class ExecutionFailure(RuntimeError):
    """The executor failed while the durable run remains recoverable."""


class CloseFailure(RuntimeError):
    """Clean close was interrupted with a durable recovery journal."""


class Executor(Protocol):
    """The one dispatch seam shared by the fixture and future provider executor."""

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Perform the one frozen mutation request."""


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    repository: Path
    packet_digest: str
    preflight_digest: str
    grant_id: str
    artifact_path: str
    expected_before: str
    desired_after: str
    allowed_paths: tuple[str, ...]
    allowed_effects: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    executor_name: str
    changed_paths: tuple[str, ...]
    observation: str

    def to_json(self) -> JsonObject:
        return {
            "changed_paths": list(self.changed_paths),
            "executor_name": self.executor_name,
            "observation": self.observation,
        }


@dataclass(frozen=True, slots=True)
class AuthorityGrant:
    id: str
    granted_by: str
    granted_at: str
    direction_id: str
    direction_digest: str
    packet_digest: str
    preflight_digest: str
    repository_id: str
    target_head: str
    target_fingerprint: str
    allowed_paths: tuple[str, ...]
    allowed_effects: tuple[str, ...]
    stop_conditions: tuple[str, ...]

    def to_json(self) -> JsonObject:
        return {
            "allowed_effects": list(self.allowed_effects),
            "allowed_paths": list(self.allowed_paths),
            "direction_digest": self.direction_digest,
            "direction_id": self.direction_id,
            "granted_at": self.granted_at,
            "granted_by": self.granted_by,
            "id": self.id,
            "packet_digest": self.packet_digest,
            "preflight_digest": self.preflight_digest,
            "repository_id": self.repository_id,
            "schema_version": 1,
            "stop_conditions": list(self.stop_conditions),
            "target_fingerprint": self.target_fingerprint,
            "target_head": self.target_head,
        }


@dataclass(frozen=True, slots=True)
class RunRecord:
    owner_id: str
    phase: str
    attempts: int
    executor_result: ExecutionResult | None
    recovery_action: str

    def to_json(self) -> JsonObject:
        return {
            "attempts": self.attempts,
            "executor_result": (
                None if self.executor_result is None else self.executor_result.to_json()
            ),
            "owner_id": self.owner_id,
            "phase": self.phase,
            "recovery_action": self.recovery_action,
        }


@dataclass(frozen=True, slots=True)
class RunState:
    draft: Draft
    basis: PreflightEnvelope
    grant: AuthorityGrant
    run: RunRecord
    route_status: str = "ready"
    direction_coverage: str = "still_remaining"
    evidence: tuple[JsonObject, ...] = ()
    residual_uncertainty: tuple[str, ...] = ()
    recovery_pressure: str = "none"
    handoff: str = "Execution is pending claim-fit evidence."
    closed: bool = False

    def to_json(self) -> JsonObject:
        return {
            "closed": self.closed,
            "direction_coverage": self.direction_coverage,
            "draft": self.draft.to_json(),
            "evidence": list(self.evidence),
            "grant": self.grant.to_json(),
            "handoff": self.handoff,
            "preflight": self.basis.to_json(),
            "recovery_pressure": self.recovery_pressure,
            "residual_uncertainty": list(self.residual_uncertainty),
            "route_status": self.route_status,
            "run": self.run.to_json(),
            "schema_version": 1,
        }


def _grant_object(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise AuthorityError("grant must be a JSON object")
    return cast(dict[str, object], value)


def _grant_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuthorityError(f"grant {field} must be a non-empty string")
    return value


def _grant_strings(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise AuthorityError(f"grant {field} must be a list of non-empty strings")
    result = tuple(cast(list[str], value))
    if len(result) != len(set(result)):
        raise AuthorityError(f"grant {field} must not contain duplicates")
    return result


def _parse_grant(value: object) -> AuthorityGrant:
    data = _grant_object(value)
    expected_keys = {
        "allowed_effects",
        "allowed_paths",
        "direction_digest",
        "direction_id",
        "granted_at",
        "granted_by",
        "id",
        "packet_digest",
        "preflight_digest",
        "repository_id",
        "schema_version",
        "stop_conditions",
        "target_fingerprint",
        "target_head",
    }
    if set(data) != expected_keys:
        raise AuthorityError("grant fields do not exactly match the authority contract")
    if data["schema_version"] != 1:
        raise AuthorityError("grant schema_version must be 1")
    return AuthorityGrant(
        id=_grant_text(data["id"], "id"),
        granted_by=_grant_text(data["granted_by"], "granted_by"),
        granted_at=_grant_text(data["granted_at"], "granted_at"),
        direction_id=_grant_text(data["direction_id"], "direction_id"),
        direction_digest=_grant_text(data["direction_digest"], "direction_digest"),
        packet_digest=_grant_text(data["packet_digest"], "packet_digest"),
        preflight_digest=_grant_text(data["preflight_digest"], "preflight_digest"),
        repository_id=_grant_text(data["repository_id"], "repository_id"),
        target_head=_grant_text(data["target_head"], "target_head"),
        target_fingerprint=_grant_text(data["target_fingerprint"], "target_fingerprint"),
        allowed_paths=_grant_strings(data["allowed_paths"], "allowed_paths"),
        allowed_effects=_grant_strings(data["allowed_effects"], "allowed_effects"),
        stop_conditions=_grant_strings(data["stop_conditions"], "stop_conditions"),
    )


def _validate_grant(grant: AuthorityGrant, draft: Draft, basis: PreflightEnvelope) -> None:
    expected: dict[str, object] = {
        "direction_id": draft.direction.id,
        "direction_digest": draft.direction_digest,
        "packet_digest": draft.packet_digest,
        "preflight_digest": basis.digest,
        "repository_id": draft.packet.repository_id,
        "target_head": basis.record.revision.head,
        "target_fingerprint": basis.record.revision.fingerprint,
        "allowed_paths": draft.packet.boundary.allowed_paths,
        "allowed_effects": draft.packet.boundary.allowed_effects,
        "stop_conditions": draft.packet.boundary.stop_conditions,
    }
    for field, expected_value in expected.items():
        if getattr(grant, field) != expected_value:
            raise AuthorityError(f"grant {field} does not match the frozen execution basis")


def _state_text(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"state {field} must be a string")
    return value


def _state_object(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValidationError(f"state {field} must be an object")
    return cast(dict[str, object], value)


def _state_list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ValidationError(f"state {field} must be a list")
    return cast(list[object], value)


def _execution_result_from_json(value: object) -> ExecutionResult:
    data = _state_object(value, "run.executor_result")
    if set(data) != {"changed_paths", "executor_name", "observation"}:
        raise ValidationError("state run.executor_result fields do not match schema version 1")
    return ExecutionResult(
        executor_name=_state_text(data["executor_name"], "run.executor_result.executor_name"),
        changed_paths=tuple(
            _state_text(item, "run.executor_result.changed_paths item")
            for item in _state_list(data["changed_paths"], "run.executor_result.changed_paths")
        ),
        observation=_state_text(data["observation"], "run.executor_result.observation"),
    )


def _run_state_from_json(value: object) -> RunState:
    data = _state_object(value, "document")
    expected_keys = {
        "closed",
        "direction_coverage",
        "draft",
        "evidence",
        "grant",
        "handoff",
        "preflight",
        "recovery_pressure",
        "residual_uncertainty",
        "route_status",
        "run",
        "schema_version",
    }
    if set(data) != expected_keys or data["schema_version"] != 1:
        raise ValidationError("state fields do not match schema version 1")
    draft = draft_from_json(data["draft"])
    basis = preflight_from_json(data["preflight"])
    grant = _parse_grant(data["grant"])
    _validate_grant(grant, draft, basis)
    run_data = _state_object(data["run"], "run")
    if set(run_data) != {
        "attempts",
        "executor_result",
        "owner_id",
        "phase",
        "recovery_action",
    }:
        raise ValidationError("state run fields do not match schema version 1")
    attempts = run_data["attempts"]
    if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 1:
        raise ValidationError("state run.attempts must be a positive integer")
    result_raw = run_data["executor_result"]
    result = None if result_raw is None else _execution_result_from_json(result_raw)
    evidence: list[JsonObject] = []
    for item in _state_list(data["evidence"], "evidence"):
        evidence.append(cast(JsonObject, _state_object(item, "evidence item")))
    residual_uncertainty = tuple(
        _state_text(item, "residual_uncertainty item")
        for item in _state_list(data["residual_uncertainty"], "residual_uncertainty")
    )
    closed = data["closed"]
    if not isinstance(closed, bool):
        raise ValidationError("state closed must be a boolean")
    return RunState(
        draft=draft,
        basis=basis,
        grant=grant,
        run=RunRecord(
            owner_id=_state_text(run_data["owner_id"], "run.owner_id"),
            phase=_state_text(run_data["phase"], "run.phase"),
            attempts=attempts,
            executor_result=result,
            recovery_action=_state_text(run_data["recovery_action"], "run.recovery_action"),
        ),
        route_status=_state_text(data["route_status"], "route_status"),
        direction_coverage=_state_text(data["direction_coverage"], "direction_coverage"),
        evidence=tuple(evidence),
        residual_uncertainty=residual_uncertainty,
        recovery_pressure=_state_text(data["recovery_pressure"], "recovery_pressure"),
        handoff=_state_text(data["handoff"], "handoff"),
        closed=closed,
    )


def load_state(repository: Path) -> RunState:
    """Load and validate the deterministic versioned state for a target."""
    store = FileStateStore(repository / ".second-mate" / "state.json")
    if not store.exists():
        raise RunConflictError("no durable run state exists for this target")
    return _run_state_from_json(store.read_json())


def _request_for(state: RunState, repository: Path) -> ExecutionRequest:
    proof = state.draft.packet.proof
    return ExecutionRequest(
        repository=repository,
        packet_digest=state.draft.packet_digest,
        preflight_digest=state.basis.digest,
        grant_id=state.grant.id,
        artifact_path=proof.artifact_path,
        expected_before=proof.before,
        desired_after=proof.after,
        allowed_paths=state.grant.allowed_paths,
        allowed_effects=state.grant.allowed_effects,
    )


def _revision_is_exact_fixture_after(state: RunState, current: TargetRevision) -> bool:
    before = state.basis.record.revision
    if current.head != before.head:
        return False
    before_files = {item.path: item for item in before.files}
    current_files = {item.path: item for item in current.files}
    if set(before_files) != set(current_files):
        return False
    artifact_path = state.draft.packet.proof.artifact_path
    for path, before_fact in before_files.items():
        current_fact = current_files[path]
        if path == artifact_path:
            expected_sha256 = hashlib.sha256(
                state.draft.packet.proof.after.encode("utf-8")
            ).hexdigest()
            if (
                current_fact.kind != "file"
                or current_fact.executable != before_fact.executable
                or current_fact.sha256 != expected_sha256
            ):
                return False
        elif current_fact != before_fact:
            return False
    return True


def _instruction_fingerprint(instructions: tuple[FileFact, ...]) -> str:
    return digest_json({"instructions": [item.to_json() for item in instructions]})


def _instructions_match_preflight(state: RunState, repository: Path) -> bool:
    return inspect_instructions(repository, state.draft) == state.basis.record.instructions


def _is_exact_fixture_after(state: RunState, repository: Path) -> bool:
    return _revision_is_exact_fixture_after(state, inspect_revision(repository))


def _record_dispatch_failure(
    store: FileStateStore, state: RunState, owner_id: str, error: Exception
) -> Never:
    failed = replace(
        state,
        run=replace(
            state.run,
            phase="failed",
            recovery_action=f"retry dispatch with owner {owner_id} after diagnosis",
        ),
        recovery_pressure="packet",
        handoff="Dispatch failed; diagnose the fixture boundary and retry with the same owner.",
    )
    store.save(failed)
    raise ExecutionFailure("dispatch failed; durable recovery state was recorded") from error


@contextmanager
def _run_lock(repository: Path) -> Iterator[None]:
    lock_path = git_private_path(repository, "second-mate-fs01.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RunConflictError("the packet run lock is held by another active owner") from error
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def restart_run(repository: Path, executor: Executor, *, owner_id: str) -> RunState:
    """Resume a failed/interrupted dispatch without transferring mutation ownership."""
    with _run_lock(repository):
        return _restart_run_locked(repository, executor, owner_id=owner_id)


def _restart_run_locked(repository: Path, executor: Executor, *, owner_id: str) -> RunState:
    state = load_state(repository)
    if state.run.owner_id != owner_id:
        raise RunConflictError("restart owner does not match the active run owner")
    if state.closed or state.run.phase not in {"active", "failed"}:
        raise RunConflictError(f"run phase {state.run.phase} cannot be restarted")
    if not _instructions_match_preflight(state, repository):
        raise AuthorityError("instruction drift blocks restart")
    store = FileStateStore(repository / ".second-mate" / "state.json")
    if inspect_revision(repository) != state.basis.record.revision:
        if not _is_exact_fixture_after(state, repository):
            raise AuthorityError("revision drift blocks restart")
        reconciled = replace(
            state,
            run=replace(
                state.run,
                phase="awaiting_evidence",
                executor_result=ExecutionResult(
                    executor_name="fixture",
                    changed_paths=(state.draft.packet.proof.artifact_path,),
                    observation="interrupted fixture dispatch reconciled from exact after state",
                ),
                recovery_action="record final-revision fixture evidence",
            ),
            recovery_pressure="none",
            handoff="Interrupted dispatch was reconciled; claim-fit evidence remains.",
        )
        store.save(reconciled)
        return reconciled
    active = replace(
        state,
        run=replace(
            state.run,
            phase="active",
            attempts=state.run.attempts + 1,
            recovery_action="restart with the same owner if dispatch is interrupted",
        ),
        recovery_pressure="none",
        handoff="Dispatch retry is active under the original owner.",
    )
    store.save(active)
    try:
        result = executor.execute(_request_for(active, repository))
    except Exception as error:
        _record_dispatch_failure(store, active, owner_id, error)
    finished = replace(
        active,
        run=replace(
            active.run,
            phase="awaiting_evidence",
            executor_result=result,
            recovery_action="record final-revision fixture evidence",
        ),
        handoff="Execution is pending claim-fit evidence.",
    )
    store.save(finished)
    return finished


def record_evidence(repository: Path) -> RunState:
    """Probe the exact after revision and persist one claim-fit fixture evidence record."""
    state = load_state(repository)
    if (
        state.run.phase == "ready_to_close"
        and state.evidence
        and state.evidence[-1]["result"] == "pass"
    ):
        return state
    if state.closed or state.run.phase not in {"awaiting_evidence", "evidence_failed"}:
        raise RunConflictError(f"run phase {state.run.phase} cannot record evidence")
    proof = state.draft.packet.proof
    failures: list[JsonValue] = []
    artifact_value: str | None = None
    sentinel_sha256: str | None = None
    try:
        artifact_value = (repository / proof.artifact_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        failures.append("fixture artifact is unavailable as UTF-8 text")
    if artifact_value is not None and artifact_value != proof.after:
        failures.append("fixture artifact does not match the declared after state")
    try:
        sentinel_sha256 = hashlib.sha256(
            (repository / proof.sentinel_path).read_bytes()
        ).hexdigest()
    except OSError:
        failures.append("fixture sentinel is unavailable")
    if sentinel_sha256 != state.basis.record.affected_baseline.sentinel_sha256:
        failures.append("fixture sentinel changed outside the grant")
    changed_paths = (
        () if state.run.executor_result is None else state.run.executor_result.changed_paths
    )
    if changed_paths != (proof.artifact_path,):
        failures.append("executor result does not identify exactly the granted artifact")
    revision = inspect_revision(repository)
    revision_matches_authority = _revision_is_exact_fixture_after(state, revision)
    if not revision_matches_authority:
        failures.append(
            "target revision is not preflight plus exactly the authorized artifact mutation"
        )
    instructions = inspect_instructions(repository, state.draft)
    instructions_match_preflight = instructions == state.basis.record.instructions
    if not instructions_match_preflight:
        failures.append("applicable instructions changed after preflight")
    result = "pass" if not failures else "fail"
    evidence: JsonObject = {
        "claim": state.draft.packet.outcome,
        "id": f"{state.draft.packet.id}-fixture-evidence-{len(state.evidence) + 1}",
        "instruction_fingerprint": _instruction_fingerprint(instructions),
        "method": "fixture-probe",
        "observation": {
            "artifact_path": proof.artifact_path,
            "artifact_sha256": (
                None
                if artifact_value is None
                else hashlib.sha256(artifact_value.encode("utf-8")).hexdigest()
            ),
            "artifact_value": artifact_value,
            "changed_paths": list(changed_paths),
            "failures": failures,
            "instructions_match_preflight": instructions_match_preflight,
            "sentinel_path": proof.sentinel_path,
            "sentinel_sha256": sentinel_sha256,
            "target_revision_matches_authority": revision_matches_authority,
        },
        "result": result,
        "target_revision": revision.to_json(),
    }
    updated = replace(
        state,
        run=replace(
            state.run,
            phase="ready_to_close" if result == "pass" else "evidence_failed",
            recovery_action=(
                "perform recoverable clean close"
                if result == "pass"
                else "repair claim-fit fixture evidence without broadening the packet"
            ),
        ),
        evidence=(*state.evidence, evidence),
        recovery_pressure="none" if result == "pass" else "packet",
        handoff=(
            "Claim-fit fixture evidence passed at the recorded target revision."
            if result == "pass"
            else "Fixture evidence failed; the packet remains open for bounded recovery."
        ),
    )
    FileStateStore(repository / ".second-mate" / "state.json").save(updated)
    return updated


_DIRECTION_COVERAGE = frozenset(
    {"proven", "explicitly_deferred", "intentionally_changed", "still_remaining"}
)


def clean_close(
    repository: Path,
    *,
    direction_coverage: str,
    residual_uncertainty: tuple[str, ...],
    handoff: str,
    store: FileStateStore | None = None,
) -> RunState:
    """Atomically or recoverably close route, evidence, pressure, and handoff together."""
    state = load_state(repository)
    if state.closed:
        return state
    if state.run.phase != "ready_to_close" or not state.evidence:
        raise RunConflictError("passing claim-fit evidence is required before clean close")
    evidence = _state_object(state.evidence[-1], "evidence item")
    if evidence.get("result") != "pass":
        raise RunConflictError("failed or uncertain evidence cannot complete the route")
    if direction_coverage not in _DIRECTION_COVERAGE:
        raise ValidationError("direction coverage status is invalid")
    if not handoff.strip():
        raise ValidationError("clean close handoff must be non-empty")
    if any(not item.strip() for item in residual_uncertainty):
        raise ValidationError("residual uncertainty entries must be non-empty")
    revision_data = _state_object(evidence.get("target_revision"), "evidence target_revision")
    evidence_fingerprint = _state_text(
        revision_data.get("fingerprint"), "evidence target_revision fingerprint"
    )
    if inspect_revision(repository).fingerprint != evidence_fingerprint:
        raise AuthorityError("revision drift after evidence blocks clean close")
    evidence_instruction_fingerprint = _state_text(
        evidence.get("instruction_fingerprint"), "evidence instruction_fingerprint"
    )
    current_instruction_fingerprint = _instruction_fingerprint(
        inspect_instructions(repository, state.draft)
    )
    if current_instruction_fingerprint != evidence_instruction_fingerprint:
        raise AuthorityError("instruction drift after evidence blocks clean close")
    closed = replace(
        state,
        run=replace(
            state.run,
            phase="closed",
            recovery_action="none; route is cleanly closed",
        ),
        route_status="completed",
        direction_coverage=direction_coverage,
        residual_uncertainty=residual_uncertainty,
        recovery_pressure="none",
        handoff=handoff,
        closed=True,
    )
    state_store = (
        FileStateStore(repository / ".second-mate" / "state.json") if store is None else store
    )
    try:
        state_store.close(state, closed)
    except Exception as error:
        raise CloseFailure("clean close was interrupted but remains recoverable") from error
    return closed


def start_run(
    *,
    draft: Draft,
    basis: PreflightEnvelope,
    grant_data: object | None,
    repository: Path,
    executor: Executor,
    owner_id: str,
) -> RunState:
    """Validate authority and revision, persist one owner, then dispatch exactly once."""
    if grant_data is None:
        raise AuthorityError("explicit consent is required before execution")
    try:
        grant = _parse_grant(grant_data)
    except ValidationError as error:
        raise AuthorityError(str(error)) from error
    _validate_grant(grant, draft, basis)
    with _run_lock(repository):
        return _start_run_locked(
            draft=draft,
            basis=basis,
            grant=grant,
            repository=repository,
            executor=executor,
            owner_id=owner_id,
        )


def _start_run_locked(
    *,
    draft: Draft,
    basis: PreflightEnvelope,
    grant: AuthorityGrant,
    repository: Path,
    executor: Executor,
    owner_id: str,
) -> RunState:
    store = FileStateStore(repository / ".second-mate" / "state.json")
    if store.exists():
        raise RunConflictError("a run state already exists for this packet")
    current_revision = inspect_revision(repository)
    if current_revision != basis.record.revision:
        raise AuthorityError("revision drift invalidated preflight and consent")
    if inspect_instructions(repository, draft) != basis.record.instructions:
        raise AuthorityError("instruction drift invalidated preflight and consent")
    if not basis.record.eligible:
        raise AuthorityError("preflight is not eligible for execution")
    if not owner_id.strip():
        raise AuthorityError("run owner_id must be a non-empty explicit identifier")

    active = RunState(
        draft=draft,
        basis=basis,
        grant=grant,
        run=RunRecord(
            owner_id=owner_id,
            phase="active",
            attempts=1,
            executor_result=None,
            recovery_action="restart with the same owner if dispatch is interrupted",
        ),
    )
    store.save(active)
    try:
        result = executor.execute(_request_for(active, repository))
    except Exception as error:
        _record_dispatch_failure(store, active, owner_id, error)
    finished = replace(
        active,
        run=replace(
            active.run,
            phase="awaiting_evidence",
            executor_result=result,
            recovery_action="record final-revision fixture evidence",
        ),
    )
    store.save(finished)
    return finished
