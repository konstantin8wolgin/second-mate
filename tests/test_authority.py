from __future__ import annotations

import copy
import shutil
from pathlib import Path

import pytest
from test_draft import valid_direction, valid_packet
from test_preflight import (
    enable_fsmonitor_fixture,
    enable_intent_to_add_fixture,
    index_flag_snapshot,
    intent_to_add_snapshot,
    make_repository,
    make_repository_with_ignored_instructions,
    run_git,
    target_snapshot,
)

import second_mate
from second_mate.domain import digest_json
from second_mate.repository import preflight_from_json


class RecordingExecutor:
    def __init__(self) -> None:
        self.requests: list[object] = []

    def execute(self, request: object) -> object:
        self.requests.append(request)
        raise AssertionError("an unauthorized executor call occurred")


def exact_grant(draft: object, basis: object) -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": "grant-1",
        "granted_by": "fixture-human",
        "granted_at": "2026-08-02T10:05:00Z",
        "direction_id": draft.direction.id,
        "direction_digest": draft.direction_digest,
        "packet_digest": draft.packet_digest,
        "preflight_digest": basis.digest,
        "repository_id": draft.packet.repository_id,
        "target_head": basis.record.revision.head,
        "target_fingerprint": basis.record.revision.fingerprint,
        "allowed_paths": list(draft.packet.boundary.allowed_paths),
        "allowed_effects": list(draft.packet.boundary.allowed_effects),
        "stop_conditions": list(draft.packet.boundary.stop_conditions),
    }


def test_start_without_explicit_consent_never_reaches_executor_or_target(tmp_path: Path) -> None:
    """Removing the consent guard must cause an observable executor call or target write."""
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    executor = RecordingExecutor()
    before = target_snapshot(repository)
    assert hasattr(second_mate, "start_run")
    assert hasattr(second_mate, "AuthorityError")

    with pytest.raises(second_mate.AuthorityError, match="explicit consent"):
        second_mate.start_run(
            draft=draft,
            basis=basis,
            grant_data=None,
            repository=repository,
            executor=executor,
            owner_id="owner-1",
        )

    assert executor.requests == []
    assert target_snapshot(repository) == before
    assert not (repository / ".second-mate").exists()


def test_mismatched_consent_never_reaches_executor_or_target(tmp_path: Path) -> None:
    """Accepting a grant for any other packet must break this authority test."""
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    grant = exact_grant(draft, basis)
    grant["packet_digest"] = "0" * 64
    executor = RecordingExecutor()
    before = target_snapshot(repository)

    with pytest.raises(second_mate.AuthorityError, match="packet_digest"):
        second_mate.start_run(
            draft=draft,
            basis=basis,
            grant_data=grant,
            repository=repository,
            executor=executor,
            owner_id="owner-1",
        )

    assert executor.requests == []
    assert target_snapshot(repository) == before
    assert not (repository / ".second-mate").exists()


def test_revision_drift_never_reaches_executor_or_adds_target_mutation(tmp_path: Path) -> None:
    """Removing the final revision check must let stale consent dispatch."""
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    grant = exact_grant(draft, basis)
    (repository / "sentinel.txt").write_text("outside drift\n", encoding="utf-8")
    after_outside_drift = target_snapshot(repository)
    executor = RecordingExecutor()

    with pytest.raises(second_mate.AuthorityError, match="revision drift"):
        second_mate.start_run(
            draft=draft,
            basis=basis,
            grant_data=grant,
            repository=repository,
            executor=executor,
            owner_id="owner-1",
        )

    assert executor.requests == []
    assert target_snapshot(repository) == after_outside_drift
    assert not (repository / ".second-mate").exists()


def test_ignored_instruction_drift_never_reaches_executor_or_target(tmp_path: Path) -> None:
    """Ignored applicable instructions remain part of the frozen execution basis."""
    repository = make_repository_with_ignored_instructions(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    grant = exact_grant(draft, basis)
    (repository / "AGENTS.md").write_text("Changed after preflight.\n", encoding="utf-8")
    after_instruction_drift = target_snapshot(repository)
    executor = RecordingExecutor()

    with pytest.raises(second_mate.AuthorityError, match="instruction drift"):
        second_mate.start_run(
            draft=draft,
            basis=basis,
            grant_data=grant,
            repository=repository,
            executor=executor,
            owner_id="owner-1",
        )

    assert executor.requests == []
    assert target_snapshot(repository) == after_instruction_drift
    assert not (repository / ".second-mate").exists()


@pytest.mark.parametrize("changed_authority", ["packet", "direction"])
def test_cross_paired_preflight_never_reaches_executor_or_target(
    tmp_path: Path, changed_authority: str
) -> None:
    """A preflight for another packet or Direction cannot authorize this draft."""
    repository = make_repository(tmp_path)
    original = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(original, repository)
    direction = copy.deepcopy(valid_direction())
    packet = copy.deepcopy(valid_packet())
    if changed_authority == "packet":
        packet["proof"]["after"] = "different authorized after\n"
    else:
        direction["text"] = "A changed approved Direction."
    changed = second_mate.create_draft(direction, packet)
    executor = RecordingExecutor()
    before = target_snapshot(repository)

    with pytest.raises(second_mate.AuthorityError, match=f"{changed_authority}.*preflight"):
        second_mate.start_run(
            draft=changed,
            basis=basis,
            grant_data=exact_grant(changed, basis),
            repository=repository,
            executor=executor,
            owner_id="owner-1",
        )

    assert executor.requests == []
    assert target_snapshot(repository) == before
    assert not (repository / ".second-mate").exists()


@pytest.mark.parametrize("contradiction", ("repository-id", "failed-baseline"))
def test_self_consistent_but_false_preflight_cannot_authorize_dispatch(
    tmp_path: Path,
    contradiction: str,
) -> None:
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    actual = second_mate.preflight(draft, repository)
    document = copy.deepcopy(actual.to_json())
    record = document["preflight"]
    assert isinstance(record, dict)
    if contradiction == "repository-id":
        record["repository_id"] = "different-repository"
    else:
        baseline = record["affected_baseline"]
        assert isinstance(baseline, dict)
        baseline["result"] = "fail"
        record["existing_failures"] = []
        record["eligible"] = True
    document["preflight_digest"] = digest_json(record)
    if contradiction == "failed-baseline":
        with pytest.raises(second_mate.ValidationError, match="baseline"):
            preflight_from_json(document)
        assert (repository / "artifact.txt").read_text(encoding="utf-8") == "before\n"
        assert not (repository / ".second-mate").exists()
        return
    forged = preflight_from_json(document)
    executor = RecordingExecutor()

    with pytest.raises(second_mate.AuthorityError, match="preflight"):
        second_mate.start_run(
            draft=draft,
            basis=forged,
            grant_data=exact_grant(draft, forged),
            repository=repository,
            executor=executor,
            owner_id="owner-1",
        )

    assert executor.requests == []
    assert (repository / "artifact.txt").read_text(encoding="utf-8") == "before\n"
    assert not (repository / ".second-mate").exists()


def test_preflight_and_grant_are_bound_to_the_observed_worktree(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    clone = tmp_path / "clone"
    shutil.copytree(repository, clone)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    executor = RecordingExecutor()

    with pytest.raises(second_mate.AuthorityError, match="current read-only preflight"):
        second_mate.start_run(
            draft=draft,
            basis=basis,
            grant_data=exact_grant(draft, basis),
            repository=clone,
            executor=executor,
            owner_id="owner-1",
        )

    assert executor.requests == []
    assert (clone / "artifact.txt").read_text(encoding="utf-8") == "before\n"
    assert not (clone / ".second-mate").exists()


@pytest.mark.parametrize(
    "basis_drift",
    (
        "branch",
        "index",
        "skip-worktree",
        "assume-unchanged",
        "fsmonitor-valid",
        "intent-to-add",
    ),
)
def test_branch_or_index_drift_invalidates_preflight_and_consent(
    tmp_path: Path,
    basis_drift: str,
) -> None:
    repository = make_repository(tmp_path)
    if basis_drift == "fsmonitor-valid":
        enable_fsmonitor_fixture(repository)
    elif basis_drift == "intent-to-add":
        enable_intent_to_add_fixture(repository)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    if basis_drift == "branch":
        run_git(repository, "switch", "-q", "-c", "same-commit-alternate")
    elif basis_drift == "index":
        artifact = repository / "artifact.txt"
        artifact.write_text("index-only drift\n", encoding="utf-8")
        run_git(repository, "add", "artifact.txt")
        artifact.write_text("before\n", encoding="utf-8")
    elif basis_drift == "fsmonitor-valid":
        before_flags = index_flag_snapshot(repository)
        run_git(repository, "update-index", "--fsmonitor-valid", "sentinel.txt")
        after_flags = index_flag_snapshot(repository)
        assert before_flags[:2] == after_flags[:2]
        assert before_flags[2] == "H sentinel.txt"
        assert after_flags[2] == "h sentinel.txt"
    elif basis_drift == "intent-to-add":
        before_intent = intent_to_add_snapshot(repository)
        run_git(repository, "add", "intent-to-add.txt")
        after_intent = intent_to_add_snapshot(repository)
        assert before_intent[:3] == after_intent[:3]
        assert before_intent[3] == ""
        assert after_intent[3] != ""
    else:
        run_git(repository, "update-index", f"--{basis_drift}", "sentinel.txt")
    executor = RecordingExecutor()

    with pytest.raises(second_mate.AuthorityError, match="revision drift"):
        second_mate.start_run(
            draft=draft,
            basis=basis,
            grant_data=exact_grant(draft, basis),
            repository=repository,
            executor=executor,
            owner_id="owner-1",
        )

    assert executor.requests == []
    assert (repository / "artifact.txt").read_text(encoding="utf-8") == "before\n"
    assert not (repository / ".second-mate").exists()
