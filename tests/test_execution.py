from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path

import pytest
from test_authority import exact_grant
from test_draft import valid_direction, valid_packet
from test_preflight import make_repository, make_repository_with_ignored_instructions, run_git

import second_mate


class CountingFixtureExecutor:
    def __init__(self) -> None:
        self.invocation_count = 0
        self.delegate = second_mate.FixtureExecutor()

    def execute(self, request: object) -> object:
        self.invocation_count += 1
        return self.delegate.execute(request)


class FailOnceFixtureExecutor:
    def __init__(self) -> None:
        self.invocation_count = 0
        self.delegate = second_mate.FixtureExecutor()

    def execute(self, request: object) -> object:
        self.invocation_count += 1
        if self.invocation_count == 1:
            raise RuntimeError("targeted fixture dispatch failure")
        return self.delegate.execute(request)


class InterruptAfterMutation:
    def __init__(self) -> None:
        self.delegate = second_mate.FixtureExecutor()

    def execute(self, request: object) -> object:
        self.delegate.execute(request)
        raise KeyboardInterrupt("simulated process interruption after mutation")


def test_exact_consent_dispatches_one_deterministic_mutation_and_persists_run(
    tmp_path: Path,
) -> None:
    """Bypassing dispatch, writing twice, or touching the sentinel must fail this journey."""
    repository = make_repository(tmp_path)
    sentinel_before = (repository / "sentinel.txt").read_bytes()
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    grant = exact_grant(draft, basis)
    assert hasattr(second_mate, "FixtureExecutor")
    executor = CountingFixtureExecutor()

    state = second_mate.start_run(
        draft=draft,
        basis=basis,
        grant_data=grant,
        repository=repository,
        executor=executor,
        owner_id="owner-1",
    )

    assert executor.invocation_count == 1
    assert (repository / "artifact.txt").read_text(encoding="utf-8") == "after\n"
    assert (repository / "sentinel.txt").read_bytes() == sentinel_before
    assert state.run.owner_id == "owner-1"
    assert state.run.phase == "awaiting_evidence"
    assert state.run.attempts == 1
    assert state.route_status == "ready"
    assert state.direction_coverage == "still_remaining"
    assert (repository / ".second-mate" / "state.json").is_file()


def test_duplicate_start_cannot_create_a_second_owner_or_invocation(tmp_path: Path) -> None:
    """Moving the existing-run guard after dispatch must invoke a second executor."""
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    grant = exact_grant(draft, basis)
    first = CountingFixtureExecutor()
    second = CountingFixtureExecutor()
    second_mate.start_run(
        draft=draft,
        basis=basis,
        grant_data=grant,
        repository=repository,
        executor=first,
        owner_id="owner-1",
    )
    assert hasattr(second_mate, "RunConflictError")

    with pytest.raises(second_mate.RunConflictError, match="already exists"):
        second_mate.start_run(
            draft=draft,
            basis=basis,
            grant_data=grant,
            repository=repository,
            executor=second,
            owner_id="owner-2",
        )

    assert first.invocation_count == 1
    assert second.invocation_count == 0


def test_executor_failure_preserves_truthful_state_and_recovery_action(tmp_path: Path) -> None:
    """Dropping failure writeback must leave an ambiguously active or falsely successful run."""
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    grant = exact_grant(draft, basis)
    executor = FailOnceFixtureExecutor()
    assert hasattr(second_mate, "ExecutionFailure")
    assert hasattr(second_mate, "load_state")

    with pytest.raises(second_mate.ExecutionFailure, match="dispatch failed"):
        second_mate.start_run(
            draft=draft,
            basis=basis,
            grant_data=grant,
            repository=repository,
            executor=executor,
            owner_id="owner-1",
        )

    state = second_mate.load_state(repository)
    assert executor.invocation_count == 1
    assert (repository / "artifact.txt").read_text(encoding="utf-8") == "before\n"
    assert state.run.phase == "failed"
    assert state.run.attempts == 1
    assert state.route_status == "ready"
    assert state.recovery_pressure == "packet"
    assert state.run.recovery_action == "retry dispatch with owner owner-1 after diagnosis"


def test_load_state_rejects_contradictory_duplicate_fields(tmp_path: Path) -> None:
    """Last-key-wins decoding must not reinterpret ambiguous durable run state."""
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
    state_path = repository / ".second-mate" / "state.json"
    document = state_path.read_text(encoding="utf-8")
    assert document.startswith('{\n  "closed": false,')
    ambiguous = document.replace(
        '{\n  "closed": false,',
        '{\n  "closed": true,\n  "closed": false,',
        1,
    )
    state_path.write_text(ambiguous, encoding="utf-8")

    with pytest.raises(RuntimeError, match=r"duplicate.*closed"):
        second_mate.load_state(repository)

    assert state_path.read_text(encoding="utf-8") == ambiguous
    assert json.loads(ambiguous)["closed"] is False


@pytest.mark.parametrize(
    "field_path",
    (
        ("schema_version",),
        ("grant", "schema_version"),
        ("preflight", "schema_version"),
        ("preflight", "preflight", "schema_version"),
    ),
)
@pytest.mark.parametrize("invalid_version", (True, 1.0))
def test_load_state_requires_literal_integer_schema_versions(
    tmp_path: Path,
    field_path: tuple[str, ...],
    invalid_version: object,
) -> None:
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
    state_path = repository / ".second-mate" / "state.json"
    document = json.loads(state_path.read_bytes())
    owner = document
    for field in field_path[:-1]:
        owner = owner[field]
        assert isinstance(owner, dict)
    owner[field_path[-1]] = invalid_version
    state_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        (second_mate.AuthorityError, second_mate.ValidationError),
        match=r"schema|integer 1",
    ):
        second_mate.load_state(repository)


def test_restart_preserves_owner_and_retries_only_the_failed_dispatch(tmp_path: Path) -> None:
    """Allowing a new owner or duplicating a completed mutation must break restart ownership."""
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    grant = exact_grant(draft, basis)
    executor = FailOnceFixtureExecutor()
    with pytest.raises(second_mate.ExecutionFailure):
        second_mate.start_run(
            draft=draft,
            basis=basis,
            grant_data=grant,
            repository=repository,
            executor=executor,
            owner_id="owner-1",
        )
    assert hasattr(second_mate, "restart_run")
    intruder = CountingFixtureExecutor()

    with pytest.raises(second_mate.RunConflictError, match="owner"):
        second_mate.restart_run(repository, intruder, owner_id="owner-2")

    assert intruder.invocation_count == 0
    resumed = second_mate.restart_run(repository, executor, owner_id="owner-1")
    assert executor.invocation_count == 2
    assert resumed.run.attempts == 2
    assert resumed.run.phase == "awaiting_evidence"
    assert resumed.recovery_pressure == "none"
    assert (repository / "artifact.txt").read_text(encoding="utf-8") == "after\n"


def test_restart_refuses_ignored_instruction_drift_before_retry(tmp_path: Path) -> None:
    """A retry cannot dispatch against instructions that changed after preflight."""
    repository = make_repository_with_ignored_instructions(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    executor = FailOnceFixtureExecutor()
    with pytest.raises(second_mate.ExecutionFailure):
        second_mate.start_run(
            draft=draft,
            basis=basis,
            grant_data=exact_grant(draft, basis),
            repository=repository,
            executor=executor,
            owner_id="owner-1",
        )
    (repository / "AGENTS.md").write_text("Changed before retry.\n", encoding="utf-8")

    with pytest.raises(second_mate.AuthorityError, match="instruction drift"):
        second_mate.restart_run(repository, executor, owner_id="owner-1")

    assert executor.invocation_count == 1
    assert second_mate.load_state(repository).run.phase == "failed"


def test_restart_reconciles_interrupted_after_state_without_duplicate_dispatch(
    tmp_path: Path,
) -> None:
    """Blindly retrying after an already-applied mutation must invoke the executor twice."""
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    with pytest.raises(KeyboardInterrupt):
        second_mate.start_run(
            draft=draft,
            basis=basis,
            grant_data=exact_grant(draft, basis),
            repository=repository,
            executor=InterruptAfterMutation(),
            owner_id="owner-1",
        )
    assert second_mate.load_state(repository).run.phase == "active"
    duplicate = CountingFixtureExecutor()

    reconciled = second_mate.restart_run(repository, duplicate, owner_id="owner-1")

    assert duplicate.invocation_count == 0
    assert reconciled.run.phase == "awaiting_evidence"
    assert reconciled.run.attempts == 1
    assert reconciled.run.executor_result is not None
    assert reconciled.run.executor_result.changed_paths == ("artifact.txt",)


def test_concurrent_run_lock_refuses_a_second_executor_owner(tmp_path: Path) -> None:
    """Removing the process lock must let start dispatch while another owner holds the boundary."""
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    grant = exact_grant(draft, basis)
    executor = CountingFixtureExecutor()
    git_lock = Path(run_git(repository, "rev-parse", "--git-path", "second-mate-mutation.lock"))
    if not git_lock.is_absolute():
        git_lock = repository / git_lock
    git_lock.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(git_lock, os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with pytest.raises(second_mate.RunConflictError, match="mutation boundary"):
            second_mate.start_run(
                draft=draft,
                basis=basis,
                grant_data=grant,
                repository=repository,
                executor=executor,
                owner_id="owner-2",
            )
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)

    assert executor.invocation_count == 0
    assert (repository / "artifact.txt").read_text(encoding="utf-8") == "before\n"
    assert not (repository / ".second-mate").exists()
