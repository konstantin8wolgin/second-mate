from __future__ import annotations

import copy
import fcntl
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from test_authority import exact_grant
from test_direction import exact_approval, exact_promotion_grant
from test_draft import valid_direction, valid_packet
from test_preflight import make_repository, run_git, target_snapshot

import second_mate
import second_mate.direction as direction_module
from second_mate.repository import git_private_path
from second_mate.store import PosixAtomicWriter, prepare_atomic_write_intent, strict_json_loads


def conversation_task() -> dict[str, object]:
    return {
        "schema_version": 1,
        "handoff_id": "conversation-task-17",
        "source_conversation_id": "conversation-42",
        "repository_id": "fixture-project",
        "task": "  Implement the approved bridge.\r\n",
        "assumptions": ["  The selected checkout is the intended project. "],
        "allowed_effects": [" Read and modify files required by the approved task. "],
        "prohibited_effects": [" Do not publish or deploy. "],
        "acceptance": [" The bridge is verified provider-free end to end. "],
    }


def approval_action(proposal: second_mate.ConversationProposal) -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": "approve-conversation-task-17",
        "decision": "approved",
        "proposal_digest": proposal.proposal_digest,
        "candidate_digest": proposal.direction_candidate.digest,
        "approved_by": "project-owner",
        "approved_at": "2026-08-07T10:00:00Z",
        "approved_scopes": ["direction_meaning", "direction_ledger_write"],
    }


def _start_fixture_run(repository: Path) -> None:
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    second_mate.start_run(
        draft=draft,
        basis=basis,
        grant_data=exact_grant(draft, basis),
        repository=repository,
        executor=second_mate.FixtureExecutor(),
        owner_id="owner-1",
    )


def _promote(
    repository: Path,
    direction_id: str,
    text: str,
    *,
    suffix: str,
    change_note: str | None,
) -> second_mate.ApprovedDirectionVersion:
    candidate = second_mate.prepare_direction(
        repository,
        text,
        direction_id=direction_id,
        change_note=change_note,
    )
    return second_mate.promote_direction(
        repository,
        candidate.to_json(),
        exact_approval(candidate, suffix=suffix),
        exact_promotion_grant(candidate, suffix=suffix),
    )


def test_find_direction_version_distinguishes_missing_current_and_superseded(
    tmp_path: Path,
) -> None:
    """Status must distinguish an absent proposal from a superseded exact version."""
    repository = make_repository(tmp_path)

    assert second_mate.find_direction_version(repository) is None

    d01 = _promote(
        repository,
        "D-01",
        "Initial task.\n",
        suffix="1",
        change_note=None,
    )
    current = second_mate.find_direction_version(repository, "D-01")
    assert current is not None
    assert current.version == d01
    assert current.is_current is True

    d02 = _promote(
        repository,
        "D-02",
        "Changed task.\n",
        suffix="2",
        change_note="Change the exact task.",
    )
    old = second_mate.find_direction_version(repository, "D-01")
    assert old is not None
    assert old.version == d01
    assert old.is_current is False
    latest = second_mate.find_direction_version(repository)
    assert latest is not None
    assert latest.version == d02
    assert latest.is_current is True


def test_find_direction_version_keeps_invalid_or_missing_recorded_history_fail_closed(
    tmp_path: Path,
) -> None:
    """A read seam must not turn corrupt or unexpectedly absent history into no history."""
    malformed_root = tmp_path / "malformed"
    malformed_root.mkdir()
    malformed = make_repository(malformed_root)
    _promote(
        malformed,
        "D-01",
        "Initial task.\n",
        suffix="1",
        change_note=None,
    )
    (malformed / ".second-mate" / "directions.json").write_text("not-json\n", encoding="utf-8")
    with pytest.raises(second_mate.ValidationError, match="history is invalid"):
        second_mate.find_direction_version(malformed)

    missing_root = tmp_path / "missing"
    missing_root.mkdir()
    missing = make_repository(missing_root)
    _promote(
        missing,
        "D-01",
        "Initial task.\n",
        suffix="1",
        change_note=None,
    )
    run_git(missing, "add", ".second-mate/directions.json")
    (missing / ".second-mate" / "directions.json").unlink()
    with pytest.raises(second_mate.DirectionConflictError, match="recorded by Git but missing"):
        second_mate.find_direction_version(missing)


def test_prepare_conversation_handoff_is_read_only_private_and_reviewable(
    tmp_path: Path,
) -> None:
    """Preparation must expose all material meaning without writing or execution authority."""
    repository = make_repository(tmp_path)
    before = target_snapshot(repository)

    proposal = second_mate.prepare_conversation_handoff(repository, conversation_task())

    assert target_snapshot(repository) == before
    assert not (repository / ".second-mate").exists()
    assert proposal.status == "awaiting-approval"
    assert proposal.summary == "Review this task. No run has started."
    assert proposal.next_action == "Approve the task meaning and one Direction-ledger write."
    assert proposal.review.task == "Implement the approved bridge."
    assert proposal.review.proposed_effects == (
        "Read and modify files required by the approved task.",
    )
    assert proposal.review.execution_authorized is False
    assert re.fullmatch(r"D-CB-[0-9a-f]{20}", proposal.direction_candidate.candidate.id)
    assert proposal.direction_candidate.candidate.change_note is None
    assert proposal.direction_candidate.candidate.text == (
        "Outcome:\n"
        "Implement the approved bridge.\n\n"
        "Assumptions:\n"
        "- The selected checkout is the intended project.\n\n"
        "Proposed effects (not execution authority):\n"
        "- Read and modify files required by the approved task.\n\n"
        "Prohibited effects:\n"
        "- Do not publish or deploy.\n\n"
        "Acceptance:\n"
        "- The bridge is verified provider-free end to end.\n\n"
        "Authority boundary:\n"
        "- Approval records task meaning and one Direction-ledger write only.\n"
        "- Route approval and Execution Consent are not granted.\n"
    )
    document = proposal.to_json()
    assert "conversation-42" not in repr(document)
    assert "transcript" not in repr(document).lower()
    assert len(proposal.source_binding_digest) == 64
    assert len(proposal.proposal_digest) == 64


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("task", "contains\x00nul"),
        ("allowed_effects", []),
        ("acceptance", ["same", "same"]),
    ],
)
def test_prepare_conversation_handoff_rejects_unsafe_or_ambiguous_text(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    """NULs, missing required scope, or duplicate meaning must not reach review."""
    repository = make_repository(tmp_path)
    task = conversation_task()
    task[field] = value

    with pytest.raises(second_mate.ValidationError):
        second_mate.prepare_conversation_handoff(repository, task)


@pytest.mark.parametrize("forbidden", ["transcript", "messages", "private_reasoning"])
def test_prepare_conversation_handoff_rejects_raw_conversation_fields(
    tmp_path: Path,
    forbidden: str,
) -> None:
    """Raw conversation and model reasoning must never enter the handoff transport."""
    repository = make_repository(tmp_path)
    task = conversation_task()
    task[forbidden] = "must stay private"

    with pytest.raises(second_mate.ValidationError, match="fields do not match"):
        second_mate.prepare_conversation_handoff(repository, task)


def test_prepare_conversation_handoff_binds_existing_direction_history(
    tmp_path: Path,
) -> None:
    """A bridge proposal in a repository with Direction history must append, not branch."""
    repository = make_repository(tmp_path)
    existing = _promote(
        repository,
        "D-01",
        "Existing approved task.\n",
        suffix="1",
        change_note=None,
    )

    proposal = second_mate.prepare_conversation_handoff(repository, conversation_task())

    assert proposal.direction_candidate.candidate.supersedes is not None
    assert proposal.direction_candidate.candidate.supersedes.direction_id == "D-01"
    assert (
        proposal.direction_candidate.candidate.supersedes.direction_digest
        == existing.direction_digest
    )
    assert proposal.direction_candidate.candidate.change_note == (
        "Adopt the newly approved conversation-derived task."
    )


def test_one_approval_stores_two_records_and_returns_non_executable_run_intent(
    tmp_path: Path,
) -> None:
    """One click must record meaning/write authority without authorizing a run."""
    repository = make_repository(tmp_path)
    proposal = second_mate.prepare_conversation_handoff(repository, conversation_task())
    before = target_snapshot(repository)

    draft = second_mate.approve_conversation_handoff(
        repository,
        proposal.to_json(),
        approval_action(proposal),
    )

    assert draft.status == "ready-for-preflight"
    assert draft.summary == "Task approved and stored. No run has started."
    assert draft.execution_authorized is False
    assert draft.run_intent.task == "Implement the approved bridge."
    assert draft.run_intent.requested_effects == (
        "Read and modify files required by the approved task.",
    )
    assert draft.authority.direction_approval.status == "recorded"
    assert draft.authority.direction_approval.record_id == (
        "approve-conversation-task-17.direction"
    )
    assert draft.authority.ledger_write_grant.status == "recorded"
    assert draft.authority.ledger_write_grant.record_id == ("approve-conversation-task-17.ledger")
    assert draft.authority.route_approval.status == "not-granted"
    assert draft.authority.execution_consent.status == "not-granted"

    after = target_snapshot(repository)
    assert before[:3] != after[:3]
    assert set(after[3]) - set(before[3]) == {".second-mate/directions.json"}
    assert all(after[3][path] == content for path, content in before[3].items())
    ledger = strict_json_loads(after[3][".second-mate/directions.json"])
    assert isinstance(ledger, dict)
    stored = ledger["versions"][0]
    assert stored["approval"]["id"] == "approve-conversation-task-17.direction"
    assert stored["approval"]["schema_version"] == 2
    assert stored["approval"]["proposal_digest"] == proposal.proposal_digest
    assert stored["promotion_grant"]["id"] == "approve-conversation-task-17.ledger"
    assert draft.run_intent.to_json().keys() == {
        "acceptance",
        "assumptions",
        "direction_digest",
        "direction_id",
        "prohibited_effects",
        "proposal_digest",
        "repository_id",
        "requested_effects",
        "schema_version",
        "task",
    }


def test_exact_repeated_approval_is_byte_identical_and_does_not_write_again(
    tmp_path: Path,
) -> None:
    """A transport retry must return the same draft without a second ledger mutation."""
    repository = make_repository(tmp_path)
    proposal = second_mate.prepare_conversation_handoff(repository, conversation_task())
    action = approval_action(proposal)
    first = second_mate.approve_conversation_handoff(repository, proposal.to_json(), action)
    ledger_path = repository / ".second-mate" / "directions.json"
    first_bytes = ledger_path.read_bytes()
    first_metadata = ledger_path.stat()
    before_retry = target_snapshot(repository)

    second = second_mate.approve_conversation_handoff(repository, proposal.to_json(), action)

    second_metadata = ledger_path.stat()
    assert second.to_json() == first.to_json()
    assert ledger_path.read_bytes() == first_bytes
    assert second_metadata.st_ino == first_metadata.st_ino
    assert second_metadata.st_mtime_ns == first_metadata.st_mtime_ns
    assert target_snapshot(repository) == before_retry


def test_exact_repeated_approval_refuses_while_shared_mutation_lock_is_held(
    tmp_path: Path,
) -> None:
    """A no-write retry must not report ready across another active mutation."""
    repository = make_repository(tmp_path)
    proposal = second_mate.prepare_conversation_handoff(repository, conversation_task())
    action = approval_action(proposal)
    second_mate.approve_conversation_handoff(repository, proposal.to_json(), action)
    before = target_snapshot(repository)
    lock_path = Path(run_git(repository, "rev-parse", "--git-path", "second-mate-mutation.lock"))
    if not lock_path.is_absolute():
        lock_path = repository / lock_path
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with pytest.raises(second_mate.ConversationConflictError, match="mutation lock"):
            second_mate.approve_conversation_handoff(
                repository,
                proposal.to_json(),
                action,
            )
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)

    assert target_snapshot(repository) == before


@pytest.mark.parametrize("changed_field", ["id", "approved_by", "approved_at"])
def test_approval_retry_with_changed_authority_conflicts_without_mutation(
    tmp_path: Path,
    changed_field: str,
) -> None:
    """A changed action must not inherit authority from an earlier approval."""
    repository = make_repository(tmp_path)
    proposal = second_mate.prepare_conversation_handoff(repository, conversation_task())
    action = approval_action(proposal)
    second_mate.approve_conversation_handoff(repository, proposal.to_json(), action)
    before = target_snapshot(repository)
    changed = copy.deepcopy(action)
    changed[changed_field] = f"different-{changed_field}"

    with pytest.raises(second_mate.ConversationConflictError):
        second_mate.approve_conversation_handoff(
            repository,
            proposal.to_json(),
            changed,
        )

    assert target_snapshot(repository) == before


@pytest.mark.parametrize(
    "scopes",
    [
        ["direction_meaning"],
        ["direction_meaning", "direction_ledger_write", "execution"],
        ["direction_ledger_write", "direction_meaning"],
        ["direction_meaning", "direction_meaning"],
    ],
)
def test_approval_requires_the_two_exact_ordered_scopes(
    tmp_path: Path,
    scopes: list[str],
) -> None:
    """Missing, extra, reordered, or duplicate scopes must never create authority."""
    repository = make_repository(tmp_path)
    proposal = second_mate.prepare_conversation_handoff(repository, conversation_task())
    action = approval_action(proposal)
    action["approved_scopes"] = scopes
    before = target_snapshot(repository)

    with pytest.raises(second_mate.ValidationError):
        second_mate.approve_conversation_handoff(
            repository,
            proposal.to_json(),
            action,
        )

    assert target_snapshot(repository) == before


@pytest.mark.parametrize("digest_field", ["proposal_digest", "candidate_digest"])
def test_approval_rejects_mismatched_digests_without_mutation(
    tmp_path: Path,
    digest_field: str,
) -> None:
    """Approval must bind both the displayed proposal and exact Direction candidate."""
    repository = make_repository(tmp_path)
    proposal = second_mate.prepare_conversation_handoff(repository, conversation_task())
    action = approval_action(proposal)
    action[digest_field] = "0" * 64
    before = target_snapshot(repository)

    with pytest.raises(second_mate.ValidationError, match="different"):
        second_mate.approve_conversation_handoff(
            repository,
            proposal.to_json(),
            action,
        )

    assert target_snapshot(repository) == before


def test_same_handoff_id_with_different_meaning_conflicts_without_mutation(
    tmp_path: Path,
) -> None:
    """An approved handoff identifier must never be rebound to changed task meaning."""
    repository = make_repository(tmp_path)
    first = second_mate.prepare_conversation_handoff(repository, conversation_task())
    changed_task = conversation_task()
    changed_task["task"] = "Implement different task meaning."
    changed = second_mate.prepare_conversation_handoff(repository, changed_task)
    assert first.direction_candidate.candidate.id == changed.direction_candidate.candidate.id
    second_mate.approve_conversation_handoff(
        repository,
        first.to_json(),
        approval_action(first),
    )
    before = target_snapshot(repository)

    with pytest.raises(second_mate.ConversationConflictError):
        second_mate.approve_conversation_handoff(
            repository,
            changed.to_json(),
            approval_action(changed),
        )

    assert target_snapshot(repository) == before


def test_same_task_from_different_source_binding_is_not_an_exact_retry(
    tmp_path: Path,
) -> None:
    """A durable approval must distinguish the exact reviewed source-bound proposal."""
    repository = make_repository(tmp_path)
    first = second_mate.prepare_conversation_handoff(repository, conversation_task())
    changed_source = conversation_task()
    changed_source["source_conversation_id"] = "conversation-99"
    second = second_mate.prepare_conversation_handoff(repository, changed_source)
    assert first.direction_candidate.digest == second.direction_candidate.digest
    assert first.proposal_digest != second.proposal_digest
    second_mate.approve_conversation_handoff(
        repository,
        first.to_json(),
        approval_action(first),
    )
    before = target_snapshot(repository)

    status = second_mate.conversation_handoff_status(repository, second.to_json())
    assert status.status == "conflict"
    with pytest.raises(second_mate.ConversationConflictError):
        second_mate.approve_conversation_handoff(
            repository,
            second.to_json(),
            approval_action(second),
        )

    assert target_snapshot(repository) == before


def test_handoff_status_is_read_only_and_distinguishes_awaiting_ready_and_conflict(
    tmp_path: Path,
) -> None:
    """Status must report stored truth without creating authority or changing the target."""
    repository = make_repository(tmp_path)
    proposal = second_mate.prepare_conversation_handoff(repository, conversation_task())
    changed_task = conversation_task()
    changed_task["task"] = "A conflicting meaning under the same handoff id."
    conflicting = second_mate.prepare_conversation_handoff(repository, changed_task)
    before = target_snapshot(repository)

    awaiting = second_mate.conversation_handoff_status(repository, proposal.to_json())
    assert awaiting.status == "awaiting-approval"
    assert awaiting.execution_authorized is False
    assert target_snapshot(repository) == before

    second_mate.approve_conversation_handoff(
        repository,
        proposal.to_json(),
        approval_action(proposal),
    )
    approved = target_snapshot(repository)
    ready = second_mate.conversation_handoff_status(repository, proposal.to_json())
    conflict = second_mate.conversation_handoff_status(repository, conflicting.to_json())
    assert ready.status == "ready-for-preflight"
    assert ready.summary == (
        "Task approved and stored. Ready for final preflight preparation; no run has started."
    )
    assert conflict.status == "conflict"
    assert target_snapshot(repository) == approved


def test_superseded_handoff_reports_status_and_cannot_be_reapproved(
    tmp_path: Path,
) -> None:
    """A superseded exact task must remain historical and never regain current authority."""
    repository = make_repository(tmp_path)
    proposal = second_mate.prepare_conversation_handoff(repository, conversation_task())
    action = approval_action(proposal)
    second_mate.approve_conversation_handoff(repository, proposal.to_json(), action)
    later = second_mate.prepare_direction(
        repository,
        "A later approved task.\n",
        direction_id="D-02",
        change_note="Replace the conversation-derived task.",
    )
    second_mate.promote_direction(
        repository,
        later.to_json(),
        exact_approval(later, suffix="2"),
        exact_promotion_grant(later, suffix="2"),
    )
    before = target_snapshot(repository)

    status = second_mate.conversation_handoff_status(repository, proposal.to_json())
    assert status.status == "superseded"
    with pytest.raises(second_mate.ConversationConflictError, match="superseded"):
        second_mate.approve_conversation_handoff(
            repository,
            proposal.to_json(),
            action,
        )

    assert target_snapshot(repository) == before


def test_approval_rejects_stale_repository_basis_and_tampered_review(
    tmp_path: Path,
) -> None:
    """Neither repository drift nor a changed display may inherit prepared authority."""
    drifted_root = tmp_path / "drifted"
    drifted_root.mkdir()
    drifted = make_repository(drifted_root)
    proposal = second_mate.prepare_conversation_handoff(drifted, conversation_task())
    (drifted / "artifact.txt").write_text("changed after review\n", encoding="utf-8")
    after_drift = target_snapshot(drifted)
    with pytest.raises(second_mate.ConversationConflictError, match="revision drift"):
        second_mate.approve_conversation_handoff(
            drifted,
            proposal.to_json(),
            approval_action(proposal),
        )
    assert target_snapshot(drifted) == after_drift

    tampered_root = tmp_path / "tampered"
    tampered_root.mkdir()
    tampered = make_repository(tampered_root)
    proposal = second_mate.prepare_conversation_handoff(tampered, conversation_task())
    document = copy.deepcopy(proposal.to_json())
    document["review"]["task"] = "Display different task meaning."
    before = target_snapshot(tampered)
    with pytest.raises(second_mate.ValidationError, match="review disagrees"):
        second_mate.approve_conversation_handoff(
            tampered,
            document,
            approval_action(proposal),
        )
    assert target_snapshot(tampered) == before


def test_open_run_blocks_first_approval_and_exact_approval_retry(tmp_path: Path) -> None:
    """An open packet run must block both a new bridge write and reuse of its authority."""
    first_root = tmp_path / "first"
    first_root.mkdir()
    first = make_repository(first_root)
    first_proposal = second_mate.prepare_conversation_handoff(first, conversation_task())
    _start_fixture_run(first)
    before = target_snapshot(first)
    with pytest.raises(second_mate.ConversationConflictError, match="open packet run"):
        second_mate.approve_conversation_handoff(
            first,
            first_proposal.to_json(),
            approval_action(first_proposal),
        )
    assert target_snapshot(first) == before

    retry_root = tmp_path / "retry"
    retry_root.mkdir()
    retry = make_repository(retry_root)
    retry_proposal = second_mate.prepare_conversation_handoff(retry, conversation_task())
    retry_action = approval_action(retry_proposal)
    second_mate.approve_conversation_handoff(
        retry,
        retry_proposal.to_json(),
        retry_action,
    )
    _start_fixture_run(retry)
    before = target_snapshot(retry)
    with pytest.raises(second_mate.ConversationConflictError, match="open packet run"):
        second_mate.approve_conversation_handoff(
            retry,
            retry_proposal.to_json(),
            retry_action,
        )
    assert target_snapshot(retry) == before


def test_bridge_approval_uses_shared_mutation_lock(tmp_path: Path) -> None:
    """Conversation import must coordinate with every other repository mutation."""
    repository = make_repository(tmp_path)
    proposal = second_mate.prepare_conversation_handoff(repository, conversation_task())
    lock_path = Path(run_git(repository, "rev-parse", "--git-path", "second-mate-mutation.lock"))
    if not lock_path.is_absolute():
        lock_path = repository / lock_path
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with pytest.raises(second_mate.ConversationConflictError, match="mutation lock"):
            second_mate.approve_conversation_handoff(
                repository,
                proposal.to_json(),
                approval_action(proposal),
            )
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)

    assert not (repository / ".second-mate").exists()


def test_concurrent_different_handoffs_leave_exactly_one_approved_version(
    tmp_path: Path,
) -> None:
    """Two simultaneous imports must serialize to one winner without overwriting history."""
    repository = make_repository(tmp_path)
    tasks = []
    for suffix in (1, 2):
        task = conversation_task()
        task["handoff_id"] = f"conversation-task-{suffix}"
        task["source_conversation_id"] = f"conversation-{suffix}"
        task["task"] = f"Implement competing task {suffix}."
        tasks.append(task)
    proposals = tuple(second_mate.prepare_conversation_handoff(repository, task) for task in tasks)
    barrier = Barrier(2)

    def approve(index: int) -> str:
        barrier.wait()
        proposal = proposals[index]
        try:
            second_mate.approve_conversation_handoff(
                repository,
                proposal.to_json(),
                approval_action(proposal),
            )
        except second_mate.ConversationConflictError:
            return "conflict"
        return "ready"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(approve, (0, 1)))

    assert sorted(results) == ["conflict", "ready"]
    ledger = strict_json_loads((repository / ".second-mate" / "directions.json").read_bytes())
    assert isinstance(ledger, dict)
    assert len(ledger["versions"]) == 1


def test_exact_bridge_retry_recovers_only_its_durably_marked_partial_write(
    tmp_path: Path,
) -> None:
    """Recovery may complete the exact intended ledger and no competing content."""
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    source_root.mkdir()
    target_root.mkdir()
    source = make_repository(source_root)
    target = make_repository(target_root)
    source_proposal = second_mate.prepare_conversation_handoff(source, conversation_task())
    target_proposal = second_mate.prepare_conversation_handoff(target, conversation_task())
    assert source_proposal.to_json() == target_proposal.to_json()
    source_draft = second_mate.approve_conversation_handoff(
        source,
        source_proposal.to_json(),
        approval_action(source_proposal),
    )
    intended = (source / ".second-mate" / "directions.json").read_bytes()
    target_path = target / ".second-mate" / "directions.json"
    intent = prepare_atomic_write_intent(
        target_path,
        intended,
        intent_directory=git_private_path(target, "second-mate-direction-intents"),
    )
    intent.scratch.write_bytes(intended[: len(intended) // 2])
    intent.scratch.chmod(0o600)

    recovered = second_mate.approve_conversation_handoff(
        target,
        target_proposal.to_json(),
        approval_action(target_proposal),
    )

    assert recovered.to_json() == source_draft.to_json()
    assert target_path.read_bytes() == intended
    assert not intent.scratch.exists()
    assert not intent.marker.exists()


def test_exact_bridge_retry_finishes_append_interrupted_after_atomic_exchange(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ready retry must retire the exact append intent before later history."""
    repository = make_repository(tmp_path)
    _promote(
        repository,
        "D-01",
        "Initial approved Direction.",
        suffix="1",
        change_note=None,
    )
    proposal = second_mate.prepare_conversation_handoff(repository, conversation_task())
    action = approval_action(proposal)
    original_exchange = PosixAtomicWriter._exchange_paths

    def interrupt_after_exchange(left: Path, right: Path) -> None:
        original_exchange(left, right)
        raise KeyboardInterrupt("simulated interruption after bridge append exchange")

    monkeypatch.setattr(
        direction_module.PosixAtomicWriter,
        "_exchange_paths",
        staticmethod(interrupt_after_exchange),
    )
    with pytest.raises(KeyboardInterrupt, match="after bridge append exchange"):
        second_mate.approve_conversation_handoff(
            repository,
            proposal.to_json(),
            action,
        )
    monkeypatch.setattr(
        direction_module.PosixAtomicWriter,
        "_exchange_paths",
        staticmethod(original_exchange),
    )
    assert tuple((repository / ".second-mate").glob("directions.json.next.*"))

    recovered = second_mate.approve_conversation_handoff(
        repository,
        proposal.to_json(),
        action,
    )

    assert recovered.status == "ready-for-preflight"
    assert not tuple((repository / ".second-mate").glob("directions.json.next.*"))
    next_candidate = second_mate.prepare_direction(
        repository,
        "Direction after recovered bridge append.",
        direction_id="D-03",
        change_note="Continue after exact bridge recovery.",
    )
    promoted = second_mate.promote_direction(
        repository,
        next_candidate.to_json(),
        exact_approval(next_candidate, suffix="3"),
        exact_promotion_grant(next_candidate, suffix="3"),
    )
    assert promoted.direction.id == "D-03"
