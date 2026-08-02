from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from test_authority import exact_grant
from test_draft import valid_direction, valid_packet
from test_execution import CountingFixtureExecutor
from test_preflight import make_repository

import second_mate
from second_mate.store import FileStateStore, PosixAtomicWriter, StateRecoveryError


def executed_repository(tmp_path: Path) -> Path:
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    second_mate.start_run(
        draft=draft,
        basis=basis,
        grant_data=exact_grant(draft, basis),
        repository=repository,
        executor=CountingFixtureExecutor(),
        owner_id="owner-1",
    )
    return repository


def test_evidence_is_claim_fit_and_bound_to_the_exact_after_revision(tmp_path: Path) -> None:
    """Omitting the after probe, sentinel check, or final revision must fail evidence."""
    repository = executed_repository(tmp_path)
    assert hasattr(second_mate, "record_evidence")

    state = second_mate.record_evidence(repository)

    assert state.run.phase == "ready_to_close"
    assert len(state.evidence) == 1
    evidence = state.evidence[0]
    assert evidence["claim"] == "Change the artifact from before to after."
    assert evidence["method"] == "fixture-probe"
    assert evidence["result"] == "pass"
    observation = evidence["observation"]
    assert observation["artifact_value"] == "after\n"
    assert observation["changed_paths"] == ["artifact.txt"]
    assert (
        observation["sentinel_sha256"]
        == hashlib.sha256(b"FIXTURE_SECRET_DO_NOT_COPY\n").hexdigest()
    )
    assert evidence["target_revision"]["fingerprint"] != state.basis.record.revision.fingerprint


def test_durable_state_is_versioned_deterministic_and_excludes_private_material(
    tmp_path: Path,
) -> None:
    """Adding private material or nondeterministic rewrites must fail inspection."""
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    state_path = repository / ".second-mate" / "state.json"
    first = state_path.read_bytes()

    second_mate.record_evidence(repository)
    second = state_path.read_bytes()

    assert second == first
    document = json.loads(second)
    assert document["schema_version"] == 1
    assert second.endswith(b"\n")
    assert b"FIXTURE_SECRET_DO_NOT_COPY" not in second
    assert b"transcript" not in second.lower()
    assert b"credential" not in second.lower()


def test_clean_close_completes_route_without_inflating_direction_proof(tmp_path: Path) -> None:
    """Coupling completed route status to proven Direction coverage must fail close."""
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    assert hasattr(second_mate, "clean_close")

    closed = second_mate.clean_close(
        repository,
        direction_coverage="still_remaining",
        residual_uncertainty=("A live provider run was not exercised.",),
        handoff="FS-01 is closed; human review remains before any provider decision.",
    )

    assert closed.closed is True
    assert closed.route_status == "completed"
    assert closed.direction_coverage == "still_remaining"
    assert closed.run.phase == "closed"
    assert len(closed.evidence) == 1
    assert closed.evidence[0]["result"] == "pass"
    assert closed.recovery_pressure == "none"
    assert closed.residual_uncertainty == ("A live provider run was not exercised.",)
    assert closed.handoff == "FS-01 is closed; human review remains before any provider decision."


class FailFinalStateWrite:
    def __init__(self) -> None:
        self.delegate = PosixAtomicWriter()

    def write(self, path: Path, content: bytes) -> None:
        if path.name == "state.json":
            raise OSError("targeted failure after close journal")
        self.delegate.write(path, content)


def test_close_failure_recovers_from_old_truthful_state_to_whole_final_state(
    tmp_path: Path,
) -> None:
    """Removing the journal must expose a false or partial completed state after this failure."""
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    state_path = repository / ".second-mate" / "state.json"
    before = state_path.read_bytes()
    failing_store = FileStateStore(state_path, writer=FailFinalStateWrite())
    assert hasattr(second_mate, "CloseFailure")

    with pytest.raises(second_mate.CloseFailure, match="recoverable"):
        second_mate.clean_close(
            repository,
            direction_coverage="still_remaining",
            residual_uncertainty=("Live provider behavior remains unexercised.",),
            handoff="Recover this journal before any continuation.",
            store=failing_store,
        )

    assert state_path.read_bytes() == before
    interrupted = json.loads(before)
    assert interrupted["route_status"] == "ready"
    assert interrupted["closed"] is False
    assert state_path.with_name("state.json.pending").is_file()

    recovered = second_mate.load_state(repository)
    assert recovered.closed is True
    assert recovered.route_status == "completed"
    assert recovered.direction_coverage == "still_remaining"
    assert recovered.evidence[0]["result"] == "pass"
    assert recovered.recovery_pressure == "none"
    assert recovered.handoff == "Recover this journal before any continuation."
    assert not state_path.with_name("state.json.pending").exists()


def test_close_recovery_rejects_contradictory_duplicate_journal_fields(
    tmp_path: Path,
) -> None:
    """Last-key-wins decoding must not authorize an ambiguous recovery journal."""
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    state_path = repository / ".second-mate" / "state.json"
    before = state_path.read_bytes()
    with pytest.raises(second_mate.CloseFailure):
        second_mate.clean_close(
            repository,
            direction_coverage="still_remaining",
            residual_uncertainty=("Live provider behavior remains unexercised.",),
            handoff="Recover this journal before any continuation.",
            store=FileStateStore(state_path, writer=FailFinalStateWrite()),
        )
    pending_path = state_path.with_name("state.json.pending")
    document = pending_path.read_text(encoding="utf-8")
    marker = '  "schema_version": 1\n}\n'
    assert document.endswith(marker)
    ambiguous = document.removesuffix(marker) + '  "schema_version": 999,\n' + marker
    pending_path.write_text(ambiguous, encoding="utf-8")

    with pytest.raises(StateRecoveryError, match=r"duplicate.*schema_version"):
        second_mate.load_state(repository)

    assert state_path.read_bytes() == before
    assert pending_path.read_text(encoding="utf-8") == ambiguous
    assert json.loads(ambiguous)["schema_version"] == 1


@pytest.mark.parametrize("invalid_version", (True, 1.0))
def test_close_recovery_requires_literal_integer_journal_schema_version(
    tmp_path: Path,
    invalid_version: object,
) -> None:
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    state_path = repository / ".second-mate" / "state.json"
    before = state_path.read_bytes()
    with pytest.raises(second_mate.CloseFailure):
        second_mate.clean_close(
            repository,
            direction_coverage="still_remaining",
            residual_uncertainty=("Live provider behavior remains unexercised.",),
            handoff="Recover this journal before any continuation.",
            store=FileStateStore(state_path, writer=FailFinalStateWrite()),
        )
    pending_path = state_path.with_name("state.json.pending")
    journal = json.loads(pending_path.read_bytes())
    journal["schema_version"] = invalid_version
    pending_path.write_text(
        json.dumps(journal, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    pending_bytes = pending_path.read_bytes()

    with pytest.raises(StateRecoveryError, match="journal schema"):
        second_mate.load_state(repository)

    assert state_path.read_bytes() == before
    assert pending_path.read_bytes() == pending_bytes


def test_failed_evidence_retries_after_bounded_repair_without_redispatch(tmp_path: Path) -> None:
    """Blocking a repaired re-probe or invoking the executor again must fail recovery."""
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    executor = CountingFixtureExecutor()
    second_mate.start_run(
        draft=draft,
        basis=basis,
        grant_data=exact_grant(draft, basis),
        repository=repository,
        executor=executor,
        owner_id="owner-1",
    )
    sentinel_path = repository / "sentinel.txt"
    sentinel_before = sentinel_path.read_bytes()
    sentinel_path.write_text("temporary out-of-boundary drift\n", encoding="utf-8")

    failed = second_mate.record_evidence(repository)

    assert executor.invocation_count == 1
    assert failed.closed is False
    assert failed.route_status == "ready"
    assert failed.run.phase == "evidence_failed"
    assert failed.recovery_pressure == "packet"
    assert [item["result"] for item in failed.evidence] == ["fail"]
    sentinel_path.write_bytes(sentinel_before)

    repaired = second_mate.record_evidence(repository)

    assert executor.invocation_count == 1
    assert repaired.closed is False
    assert repaired.route_status == "ready"
    assert repaired.run.phase == "ready_to_close"
    assert repaired.recovery_pressure == "none"
    assert [item["result"] for item in repaired.evidence] == ["fail", "pass"]
    closed = second_mate.clean_close(
        repository,
        direction_coverage="still_remaining",
        residual_uncertainty=("The repaired evidence failure remains recorded.",),
        handoff="Bounded evidence recovery completed without redispatch.",
    )
    assert closed.closed is True
    assert closed.route_status == "completed"
    assert [item["result"] for item in closed.evidence] == ["fail", "pass"]
