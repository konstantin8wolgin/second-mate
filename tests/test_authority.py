from __future__ import annotations

from pathlib import Path

import pytest
from test_draft import valid_direction, valid_packet
from test_preflight import (
    make_repository,
    make_repository_with_ignored_instructions,
    target_snapshot,
)

import second_mate


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
