"""Authority-guarded dispatch for one FS-01 run."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Never, Protocol, cast

from second_mate.domain import (
    Draft,
    JsonObject,
    ValidationError,
    digest_json,
    draft_from_json,
)
from second_mate.repository import (
    FileFact,
    MutationLockBusyError,
    PreflightEnvelope,
    TargetRevision,
    git_private_path,
    inspect_fixture_paths,
    inspect_instructions,
    inspect_revision,
    mutation_lock,
    preflight,
    preflight_from_json,
)
from second_mate.store import (
    FileStateStore,
    deterministic_document_bytes,
    recovery_intent_paths,
)


class AuthorityError(RuntimeError):
    """Execution authority is missing, stale, or does not match the frozen basis."""


class RunConflictError(RuntimeError):
    """Another durable owner already holds this packet's mutation boundary."""


class ExecutionFailure(RuntimeError):
    """The executor failed while the durable run remains recoverable."""


class CloseFailure(RuntimeError):
    """Clean close was interrupted with a durable recovery journal."""


_RUN_PHASES = frozenset(
    {"active", "failed", "awaiting_evidence", "evidence_failed", "ready_to_close", "closed"}
)
_ROUTE_STATUSES = frozenset({"ready", "completed"})
_FS01_DIRECTION_COVERAGE = frozenset({"still_remaining"})
_RECOVERY_PRESSURES = frozenset({"none", "packet"})
_FS01_REQUIRED_RESIDUAL_UNCERTAINTY = frozenset(
    {
        "Human product review remains outstanding.",
        "Live provider behavior was not exercised.",
    }
)
_RUN_STATE_SCHEMA_VERSION = 2
_INTENT_DIRECTORY_NAME = "second-mate-fs01-intents"


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
            "schema_version": _RUN_STATE_SCHEMA_VERSION,
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
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise AuthorityError("grant schema_version must be the integer 1")
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
    if basis.record.repository_id != draft.packet.repository_id:
        raise AuthorityError("repository identity does not match the preflight basis")
    if basis.record.direction_digest != draft.direction_digest:
        raise AuthorityError("direction digest does not match the preflight basis")
    if basis.record.packet_digest != draft.packet_digest:
        raise AuthorityError("packet digest does not match the preflight basis")
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


def _validate_persisted_basis(draft: Draft, basis: PreflightEnvelope) -> None:
    record = basis.record
    baseline = record.affected_baseline
    proof = draft.packet.proof
    if not record.eligible:
        raise ValidationError("durable run preflight must be eligible")
    if baseline.result != "pass" or record.existing_failures:
        raise ValidationError("durable run preflight baseline must pass without failures")
    if record.irreversible_change_required:
        raise ValidationError("durable run preflight cannot require an irreversible change")
    if (
        baseline.artifact_path != proof.artifact_path
        or baseline.sentinel_path != proof.sentinel_path
    ):
        raise ValidationError("durable run preflight baseline does not match its proof paths")
    if baseline.artifact_value != proof.before:
        raise ValidationError(
            "durable run preflight baseline does not match the proof before value"
        )
    if baseline.sentinel_sha256 is None:
        raise ValidationError("durable run preflight baseline omits the sentinel hash")
    revision_files = {item.path: item for item in record.revision.files}
    artifact = revision_files.get(proof.artifact_path)
    sentinel = revision_files.get(proof.sentinel_path)
    if (
        artifact is None
        or artifact.kind != "file"
        or artifact.sha256 != hashlib.sha256(proof.before.encode("utf-8")).hexdigest()
    ):
        raise ValidationError("durable run preflight artifact baseline contradicts its revision")
    if sentinel is None or sentinel.kind != "file" or sentinel.sha256 != baseline.sentinel_sha256:
        raise ValidationError("durable run preflight sentinel baseline contradicts its revision")


def _state_text(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"state {field} must be a string")
    return value


def _state_nonempty_text(value: object, field: str) -> str:
    result = _state_text(value, field)
    if not result.strip():
        raise ValidationError(f"state {field} must be non-empty")
    return result


def _state_choice(value: object, field: str, choices: frozenset[str]) -> str:
    result = _state_text(value, field)
    if result not in choices:
        raise ValidationError(f"state {field} is invalid")
    return result


def _state_object(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValidationError(f"state {field} must be an object")
    return cast(dict[str, object], value)


def _state_list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ValidationError(f"state {field} must be a list")
    return cast(list[object], value)


def _state_bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"state {field} must be a boolean")
    return value


def _state_sha256(value: object, field: str) -> str:
    result = _state_text(value, field)
    if len(result) != 64 or any(character not in "0123456789abcdef" for character in result):
        raise ValidationError(f"state {field} must be a lowercase SHA-256 digest")
    return result


def _evidence_file_fact_from_json(value: object) -> FileFact:
    data = _state_object(value, "evidence target_revision file")
    if set(data) != {"executable", "kind", "path", "sha256"}:
        raise ValidationError("state evidence target_revision file fields are invalid")
    return FileFact(
        path=_state_nonempty_text(data["path"], "evidence target_revision file path"),
        kind=_state_choice(
            data["kind"],
            "evidence target_revision file kind",
            frozenset({"file", "symlink", "missing"}),
        ),
        sha256=_state_sha256(data["sha256"], "evidence target_revision file sha256"),
        executable=_state_bool(data["executable"], "evidence target_revision file executable"),
    )


def _evidence_revision_from_json(value: object) -> TargetRevision:
    data = _state_object(value, "evidence target_revision")
    if set(data) != {"branch", "files", "fingerprint", "head", "index_sha256"}:
        raise ValidationError("state evidence target_revision fields are invalid")
    files = tuple(
        _evidence_file_fact_from_json(item)
        for item in _state_list(data["files"], "evidence target_revision files")
    )
    paths = tuple(item.path for item in files)
    if paths != tuple(sorted(paths)) or len(paths) != len(set(paths)):
        raise ValidationError("state evidence target_revision files must be unique and sorted")
    revision = TargetRevision(
        head=_state_nonempty_text(data["head"], "evidence target_revision head"),
        branch=_state_nonempty_text(data["branch"], "evidence target_revision branch"),
        index_sha256=_state_sha256(data["index_sha256"], "evidence target_revision index_sha256"),
        fingerprint=_state_sha256(data["fingerprint"], "evidence target_revision fingerprint"),
        files=files,
    )
    expected_fingerprint = digest_json(
        {
            "branch": revision.branch,
            "files": [item.to_json() for item in revision.files],
            "head": revision.head,
            "index_sha256": revision.index_sha256,
        }
    )
    if revision.fingerprint != expected_fingerprint:
        raise ValidationError("state evidence target_revision fingerprint is invalid")
    return revision


def _fixture_evidence_failures(
    *,
    draft: Draft,
    basis: PreflightEnvelope,
    artifact_path_safe: bool,
    artifact_value: str | None,
    sentinel_path_safe: bool,
    sentinel_sha256: str | None,
    changed_paths: tuple[str, ...],
    revision_inspected: bool,
    revision_matches_authority: bool,
    instructions_inspected: bool,
    instructions_match_preflight: bool,
) -> tuple[str, ...]:
    failures: list[str] = []
    if not artifact_path_safe:
        failures.append(
            "fixture artifact path must be one unaliased regular file at its declared path"
        )
    elif artifact_value is None:
        failures.append("fixture artifact is unavailable as UTF-8 text")
    elif artifact_value != draft.packet.proof.after:
        failures.append("fixture artifact does not match the declared after state")
    if not sentinel_path_safe:
        failures.append(
            "fixture sentinel path must be one unaliased regular file at its declared path"
        )
    elif sentinel_sha256 is None:
        failures.append("fixture sentinel is unavailable")
    elif sentinel_sha256 != basis.record.affected_baseline.sentinel_sha256:
        failures.append("fixture sentinel changed outside the grant")
    if changed_paths != (draft.packet.proof.artifact_path,):
        failures.append("executor result does not identify exactly the granted artifact")
    if not revision_inspected:
        failures.append("target revision could not be safely inspected")
    elif not revision_matches_authority:
        failures.append(
            "target revision is not preflight plus exactly the authorized artifact mutation"
        )
    if not instructions_inspected:
        failures.append("applicable instructions could not be safely inspected")
    elif not instructions_match_preflight:
        failures.append("applicable instructions changed after preflight")
    return tuple(failures)


def _evidence_from_json(
    value: object,
    *,
    draft: Draft,
    basis: PreflightEnvelope,
    executor_result: ExecutionResult | None,
    index: int,
) -> JsonObject:
    data = _state_object(value, "evidence item")
    if set(data) != {
        "claim",
        "id",
        "instruction_fingerprint",
        "method",
        "observation",
        "result",
        "target_revision",
    }:
        raise ValidationError("state evidence fields do not match the expected schema")
    if _state_text(data["claim"], "evidence claim") != draft.packet.outcome:
        raise ValidationError("state evidence claim does not match the frozen packet")
    expected_id = f"{draft.packet.id}-fixture-evidence-{index}"
    if _state_nonempty_text(data["id"], "evidence id") != expected_id:
        raise ValidationError("state evidence id does not match its durable sequence")
    if _state_text(data["method"], "evidence method") != "fixture-probe":
        raise ValidationError("state evidence method is invalid")
    result = _state_choice(data["result"], "evidence result", frozenset({"pass", "fail"}))
    instruction_fingerprint_raw = data["instruction_fingerprint"]
    instruction_fingerprint = (
        None
        if instruction_fingerprint_raw is None
        else _state_sha256(
            instruction_fingerprint_raw,
            "evidence instruction_fingerprint",
        )
    )
    revision_raw = data["target_revision"]
    revision = None if revision_raw is None else _evidence_revision_from_json(revision_raw)
    observation = _state_object(data["observation"], "evidence observation")
    if set(observation) != {
        "artifact_path",
        "artifact_path_safe",
        "artifact_sha256",
        "artifact_value",
        "changed_paths",
        "failures",
        "instructions_match_preflight",
        "sentinel_path",
        "sentinel_path_safe",
        "sentinel_sha256",
        "target_revision_matches_authority",
    }:
        raise ValidationError("state evidence observation fields are invalid")
    proof = draft.packet.proof
    if _state_text(observation["artifact_path"], "evidence artifact_path") != proof.artifact_path:
        raise ValidationError("state evidence artifact path is invalid")
    if _state_text(observation["sentinel_path"], "evidence sentinel_path") != proof.sentinel_path:
        raise ValidationError("state evidence sentinel path is invalid")
    artifact_value_raw = observation["artifact_value"]
    if artifact_value_raw is not None and not isinstance(artifact_value_raw, str):
        raise ValidationError("state evidence artifact value must be a string or null")
    artifact_sha_raw = observation["artifact_sha256"]
    artifact_sha = (
        None
        if artifact_sha_raw is None
        else _state_sha256(artifact_sha_raw, "evidence artifact_sha256")
    )
    if artifact_value_raw is None:
        if artifact_sha is not None:
            raise ValidationError("state evidence artifact hash requires an artifact value")
    elif artifact_sha != hashlib.sha256(artifact_value_raw.encode("utf-8")).hexdigest():
        raise ValidationError("state evidence artifact hash does not match its value")
    changed_paths = tuple(
        _state_nonempty_text(item, "evidence changed_paths item")
        for item in _state_list(observation["changed_paths"], "evidence changed_paths")
    )
    if executor_result is None or changed_paths != executor_result.changed_paths:
        raise ValidationError("state evidence changed paths contradict the durable executor result")
    failures = tuple(
        _state_nonempty_text(item, "evidence failures item")
        for item in _state_list(observation["failures"], "evidence failures")
    )
    instructions_match = _state_bool(
        observation["instructions_match_preflight"],
        "evidence instructions_match_preflight",
    )
    revision_matches = _state_bool(
        observation["target_revision_matches_authority"],
        "evidence target_revision_matches_authority",
    )
    sentinel_sha_raw = observation["sentinel_sha256"]
    sentinel_sha = (
        None
        if sentinel_sha_raw is None
        else _state_sha256(sentinel_sha_raw, "evidence sentinel_sha256")
    )
    artifact_path_safe = _state_bool(
        observation["artifact_path_safe"], "evidence artifact_path_safe"
    )
    sentinel_path_safe = _state_bool(
        observation["sentinel_path_safe"], "evidence sentinel_path_safe"
    )
    if sentinel_path_safe != (sentinel_sha is not None):
        raise ValidationError("state evidence sentinel path safety contradicts its recorded hash")
    if (
        not artifact_path_safe and (artifact_value_raw is not None or artifact_sha is not None)
    ) or (not sentinel_path_safe and sentinel_sha is not None):
        raise ValidationError("state unsafe evidence path must not retain read-through content")
    instructions_inspected = instruction_fingerprint is not None
    revision_inspected = revision is not None
    actual_instructions_match = (
        instruction_fingerprint == _instruction_fingerprint(basis.record.instructions)
        if instructions_inspected
        else False
    )
    actual_revision_matches = (
        _revision_is_exact_fixture_after_basis(draft, basis, revision)
        if revision is not None
        else False
    )
    if (
        instructions_match != actual_instructions_match
        or revision_matches != actual_revision_matches
    ):
        raise ValidationError("state evidence match flags contradict their recorded facts")
    expected_failures = _fixture_evidence_failures(
        draft=draft,
        basis=basis,
        artifact_path_safe=artifact_path_safe,
        artifact_value=artifact_value_raw,
        sentinel_path_safe=sentinel_path_safe,
        sentinel_sha256=sentinel_sha,
        changed_paths=changed_paths,
        revision_inspected=revision_inspected,
        revision_matches_authority=revision_matches,
        instructions_inspected=instructions_inspected,
        instructions_match_preflight=instructions_match,
    )
    expected_result = "pass" if not expected_failures else "fail"
    if failures != expected_failures or result != expected_result:
        raise ValidationError("state evidence result or failures contradict its observation")
    return cast(JsonObject, data)


def _execution_result_from_json(value: object) -> ExecutionResult:
    data = _state_object(value, "run.executor_result")
    if set(data) != {"changed_paths", "executor_name", "observation"}:
        raise ValidationError("state run.executor_result fields do not match the expected schema")
    return ExecutionResult(
        executor_name=_state_text(data["executor_name"], "run.executor_result.executor_name"),
        changed_paths=tuple(
            _state_text(item, "run.executor_result.changed_paths item")
            for item in _state_list(data["changed_paths"], "run.executor_result.changed_paths")
        ),
        observation=_state_text(data["observation"], "run.executor_result.observation"),
    )


def _validate_fixture_executor_result(value: object, draft: Draft) -> ExecutionResult:
    if not isinstance(value, ExecutionResult):
        raise ValidationError("fixture executor result must use the execution result contract")
    if (
        value.executor_name != "fixture"
        or value.changed_paths != (draft.packet.proof.artifact_path,)
        or not value.observation.strip()
    ):
        raise ValidationError("fixture executor result is invalid")
    return value


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
    if (
        set(data) != expected_keys
        or type(data["schema_version"]) is not int
        or data["schema_version"] != _RUN_STATE_SCHEMA_VERSION
    ):
        raise ValidationError("state fields do not match schema version 2")
    draft = draft_from_json(data["draft"])
    basis = preflight_from_json(data["preflight"])
    _validate_persisted_basis(draft, basis)
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
        raise ValidationError("state run fields do not match the expected schema")
    attempts = run_data["attempts"]
    if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 1:
        raise ValidationError("state run.attempts must be a positive integer")
    result_raw = run_data["executor_result"]
    result = None if result_raw is None else _execution_result_from_json(result_raw)
    if result is not None:
        _validate_fixture_executor_result(result, draft)
    evidence = [
        _evidence_from_json(
            item,
            draft=draft,
            basis=basis,
            executor_result=result,
            index=index,
        )
        for index, item in enumerate(_state_list(data["evidence"], "evidence"), start=1)
    ]
    if any(item["result"] == "pass" for item in evidence[:-1]):
        raise ValidationError("state cannot append evidence after passing evidence")
    residual_uncertainty = tuple(
        _state_nonempty_text(item, "residual_uncertainty item")
        for item in _state_list(data["residual_uncertainty"], "residual_uncertainty")
    )
    if len(residual_uncertainty) != len(set(residual_uncertainty)):
        raise ValidationError("state residual uncertainty must not contain duplicates")
    closed = data["closed"]
    if not isinstance(closed, bool):
        raise ValidationError("state closed must be a boolean")
    phase = _state_choice(run_data["phase"], "run.phase", _RUN_PHASES)
    route_status = _state_choice(data["route_status"], "route_status", _ROUTE_STATUSES)
    direction_coverage = _state_choice(
        data["direction_coverage"], "direction_coverage", _FS01_DIRECTION_COVERAGE
    )
    recovery_pressure = _state_choice(
        data["recovery_pressure"], "recovery_pressure", _RECOVERY_PRESSURES
    )
    owner_id = _state_nonempty_text(run_data["owner_id"], "run.owner_id")
    recovery_action = _state_nonempty_text(run_data["recovery_action"], "run.recovery_action")
    handoff = _state_nonempty_text(data["handoff"], "handoff")
    closed_markers_are_consistent = (
        phase == "closed" and route_status == "completed"
        if closed
        else phase != "closed" and route_status != "completed"
    )
    if not closed_markers_are_consistent:
        raise ValidationError(
            "state closed status is inconsistent with its run phase and route status"
        )
    if bool(residual_uncertainty) != closed:
        raise ValidationError("state residual uncertainty must be present exactly at clean close")
    if closed and not _FS01_REQUIRED_RESIDUAL_UNCERTAINTY.issubset(residual_uncertainty):
        raise ValidationError("state clean close omits required FS-01 limitations")
    phase_has_result = phase in {
        "awaiting_evidence",
        "evidence_failed",
        "ready_to_close",
        "closed",
    }
    phase_has_evidence = phase in {"evidence_failed", "ready_to_close", "closed"}
    expected_pressure = "packet" if phase in {"failed", "evidence_failed"} else "none"
    if (
        (result is not None) != phase_has_result
        or bool(evidence) != phase_has_evidence
        or recovery_pressure != expected_pressure
    ):
        raise ValidationError(
            "state lifecycle is inconsistent across phase, result, evidence, and pressure"
        )
    if evidence:
        expected_evidence_result = "fail" if phase == "evidence_failed" else "pass"
        if evidence[-1]["result"] != expected_evidence_result:
            raise ValidationError("state phase does not match its latest evidence result")
    return RunState(
        draft=draft,
        basis=basis,
        grant=grant,
        run=RunRecord(
            owner_id=owner_id,
            phase=phase,
            attempts=attempts,
            executor_result=result,
            recovery_action=recovery_action,
        ),
        route_status=route_status,
        direction_coverage=direction_coverage,
        evidence=tuple(evidence),
        residual_uncertainty=residual_uncertainty,
        recovery_pressure=recovery_pressure,
        handoff=handoff,
        closed=closed,
    )


def _validate_state_target(state: RunState, repository: Path) -> None:
    if state.basis.record.target_root != os.fspath(repository.resolve()):
        raise AuthorityError("durable run state belongs to a different target worktree")


def _validate_recovered_close(
    base_value: object,
    final_value: object,
    repository: Path,
) -> None:
    base = _run_state_from_json(base_value)
    final = _run_state_from_json(final_value)
    _validate_state_target(base, repository)
    _validate_state_target(final, repository)
    if base.closed or base.run.phase != "ready_to_close" or not base.evidence:
        raise ValidationError("close recovery base is not ready for clean close")
    expected = replace(
        base,
        run=replace(
            base.run,
            phase="closed",
            recovery_action="none; route is cleanly closed",
        ),
        route_status="completed",
        direction_coverage=final.direction_coverage,
        residual_uncertainty=final.residual_uncertainty,
        recovery_pressure="none",
        handoff=final.handoff,
        closed=True,
    )
    if final != expected:
        raise ValidationError("journal does not contain the sole legal clean-close transition")


def _state_store(
    repository: Path,
    *,
    recovery_validator: Callable[[object, object], None] | None = None,
) -> FileStateStore:
    root = repository.resolve()
    return FileStateStore(
        root / ".second-mate" / "state.json",
        intent_directory=git_private_path(root, _INTENT_DIRECTORY_NAME),
        recovery_validator=recovery_validator,
    )


def load_state(repository: Path) -> RunState:
    """Load and validate the deterministic versioned state for a target."""
    root = repository.resolve()
    with _run_lock(root):
        return _load_state_locked(root)


def _load_state_locked(repository: Path) -> RunState:
    root = repository.resolve()

    def validate_recovery(base_value: object, final_value: object) -> None:
        _validate_recovered_close(base_value, final_value, root)

    store = _state_store(root, recovery_validator=validate_recovery)
    if not store.exists():
        raise RunConflictError("no durable run state exists for this target")
    state = _run_state_from_json(store.read_json())
    _validate_state_target(state, root)
    return state


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
    return _revision_is_exact_fixture_after_basis(state.draft, state.basis, current)


def _revision_is_exact_fixture_after_basis(
    draft: Draft, basis: PreflightEnvelope, current: TargetRevision
) -> bool:
    before = basis.record.revision
    if (
        current.head != before.head
        or current.branch != before.branch
        or current.index_sha256 != before.index_sha256
    ):
        return False
    before_files = {item.path: item for item in before.files}
    current_files = {item.path: item for item in current.files}
    if set(before_files) != set(current_files):
        return False
    artifact_path = draft.packet.proof.artifact_path
    for path, before_fact in before_files.items():
        current_fact = current_files[path]
        if path == artifact_path:
            expected_sha256 = hashlib.sha256(draft.packet.proof.after.encode("utf-8")).hexdigest()
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
    try:
        with mutation_lock(repository):
            yield
    except MutationLockBusyError as error:
        raise RunConflictError(str(error)) from error


def restart_run(repository: Path, executor: Executor, *, owner_id: str) -> RunState:
    """Resume a failed/interrupted dispatch without transferring mutation ownership."""
    root = repository.resolve()
    with _run_lock(root):
        return _restart_run_locked(root, executor, owner_id=owner_id)


def _restart_run_locked(repository: Path, executor: Executor, *, owner_id: str) -> RunState:
    state = _load_state_locked(repository)
    if state.run.owner_id != owner_id:
        raise RunConflictError("restart owner does not match the active run owner")
    if state.closed or state.run.phase not in {"active", "failed"}:
        raise RunConflictError(f"run phase {state.run.phase} cannot be restarted")
    if not _instructions_match_preflight(state, repository):
        raise AuthorityError("instruction drift blocks restart")
    store = _state_store(repository)
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
        result = _validate_fixture_executor_result(
            executor.execute(_request_for(active, repository)),
            active.draft,
        )
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
    root = repository.resolve()
    with _run_lock(root):
        return _record_evidence_locked(root)


def _record_evidence_locked(repository: Path) -> RunState:
    state = _load_state_locked(repository)
    if (
        state.run.phase == "ready_to_close"
        and state.evidence
        and state.evidence[-1]["result"] == "pass"
    ):
        return state
    if state.closed or state.run.phase not in {"awaiting_evidence", "evidence_failed"}:
        raise RunConflictError(f"run phase {state.run.phase} cannot record evidence")
    proof = state.draft.packet.proof
    fixture_paths = inspect_fixture_paths(repository, state.draft)
    artifact_path_safe = fixture_paths.artifact is not None
    sentinel_path_safe = fixture_paths.sentinel is not None
    artifact_value: str | None = None
    sentinel_sha256: str | None = None
    if fixture_paths.artifact is not None:
        with suppress(UnicodeError):
            artifact_value = fixture_paths.artifact.decode("utf-8")
    if fixture_paths.sentinel is not None:
        sentinel_sha256 = hashlib.sha256(fixture_paths.sentinel).hexdigest()
    changed_paths = (
        () if state.run.executor_result is None else state.run.executor_result.changed_paths
    )
    revision: TargetRevision | None
    try:
        revision = inspect_revision(repository)
    except (OSError, ValidationError):
        revision = None
    revision_matches_authority = (
        _revision_is_exact_fixture_after(state, revision) if revision is not None else False
    )
    instructions: tuple[FileFact, ...] | None
    try:
        instructions = inspect_instructions(repository, state.draft)
    except (OSError, ValidationError):
        instructions = None
    instructions_match_preflight = (
        instructions == state.basis.record.instructions if instructions is not None else False
    )
    failures = _fixture_evidence_failures(
        draft=state.draft,
        basis=state.basis,
        artifact_path_safe=artifact_path_safe,
        artifact_value=artifact_value,
        sentinel_path_safe=sentinel_path_safe,
        sentinel_sha256=sentinel_sha256,
        changed_paths=changed_paths,
        revision_inspected=revision is not None,
        revision_matches_authority=revision_matches_authority,
        instructions_inspected=instructions is not None,
        instructions_match_preflight=instructions_match_preflight,
    )
    result = "pass" if not failures else "fail"
    evidence: JsonObject = {
        "claim": state.draft.packet.outcome,
        "id": f"{state.draft.packet.id}-fixture-evidence-{len(state.evidence) + 1}",
        "instruction_fingerprint": (
            None if instructions is None else _instruction_fingerprint(instructions)
        ),
        "method": "fixture-probe",
        "observation": {
            "artifact_path": proof.artifact_path,
            "artifact_path_safe": artifact_path_safe,
            "artifact_sha256": (
                None
                if artifact_value is None
                else hashlib.sha256(artifact_value.encode("utf-8")).hexdigest()
            ),
            "artifact_value": artifact_value,
            "changed_paths": list(changed_paths),
            "failures": list(failures),
            "instructions_match_preflight": instructions_match_preflight,
            "sentinel_path": proof.sentinel_path,
            "sentinel_path_safe": sentinel_path_safe,
            "sentinel_sha256": sentinel_sha256,
            "target_revision_matches_authority": revision_matches_authority,
        },
        "result": result,
        "target_revision": None if revision is None else revision.to_json(),
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
    _state_store(repository).save(updated)
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
    root = repository.resolve()
    with _run_lock(root):
        return _clean_close_locked(
            root,
            direction_coverage=direction_coverage,
            residual_uncertainty=residual_uncertainty,
            handoff=handoff,
            store=store,
        )


def _clean_close_locked(
    repository: Path,
    *,
    direction_coverage: str,
    residual_uncertainty: tuple[str, ...],
    handoff: str,
    store: FileStateStore | None,
) -> RunState:
    state = _load_state_locked(repository)
    if state.closed:
        return state
    if state.run.phase != "ready_to_close" or not state.evidence:
        raise RunConflictError("passing claim-fit evidence is required before clean close")
    evidence = _state_object(state.evidence[-1], "evidence item")
    if evidence.get("result") != "pass":
        raise RunConflictError("failed or uncertain evidence cannot complete the route")
    if direction_coverage not in _DIRECTION_COVERAGE:
        raise ValidationError("direction coverage status is invalid")
    if direction_coverage != "still_remaining":
        raise ValidationError(
            "FS-01 fixture close supports only still_remaining Direction coverage"
        )
    if not handoff.strip():
        raise ValidationError("clean close handoff must be non-empty")
    if (
        not residual_uncertainty
        or any(not item.strip() for item in residual_uncertainty)
        or len(set(residual_uncertainty)) != len(residual_uncertainty)
        or not _FS01_REQUIRED_RESIDUAL_UNCERTAINTY.issubset(residual_uncertainty)
    ):
        raise ValidationError(
            "residual uncertainty must include the required FS-01 limitations exactly once"
        )
    if store is not None:
        expected_path = (repository.resolve() / ".second-mate" / "state.json").absolute()
        if store.path != expected_path:
            raise ValidationError("clean close store must use the target state path")
        expected_intent_directory = git_private_path(repository, _INTENT_DIRECTORY_NAME).absolute()
        if store.intent_directory != expected_intent_directory:
            raise ValidationError("clean close store must use the target intent directory")
    fixture_paths = inspect_fixture_paths(repository, state.draft)
    if fixture_paths.failures:
        raise AuthorityError("fixture path identity drift after evidence blocks clean close")
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
    state_store = _state_store(repository) if store is None else store
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
    root = repository.resolve()
    with _run_lock(root):
        return _start_run_locked(
            draft=draft,
            basis=basis,
            grant=grant,
            repository=root,
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
    store = _state_store(repository)
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
    active_content = deterministic_document_bytes(active)
    recovery_intents = recovery_intent_paths(
        store.path,
        active_content,
        intent_directory=store.intent_directory,
    )
    current_basis = preflight(
        draft,
        repository,
        _recovery_intents=frozenset(
            recovery_intent.relative_to(repository).as_posix()
            for recovery_intent in recovery_intents
        ),
    )
    if current_basis != basis:
        raise AuthorityError("supplied basis does not match the current read-only preflight")
    store.save(active)
    try:
        result = _validate_fixture_executor_result(
            executor.execute(_request_for(active, repository)),
            active.draft,
        )
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
