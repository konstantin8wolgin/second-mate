from __future__ import annotations

import re
from pathlib import Path

import pytest
from test_direction import exact_approval, exact_promotion_grant
from test_preflight import make_repository, run_git, target_snapshot

import second_mate


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
