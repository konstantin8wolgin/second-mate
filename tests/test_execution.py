from __future__ import annotations

import fcntl
import json
import os
import shutil
from pathlib import Path

import pytest
from test_authority import exact_grant
from test_draft import valid_direction, valid_packet
from test_preflight import make_repository, make_repository_with_ignored_instructions, run_git

import second_mate
import second_mate.store as store_module
from second_mate.domain import digest_json
from second_mate.service import ExecutionResult
from second_mate.store import (
    AtomicWriteIntent,
    PosixAtomicWriter,
    StateRecoveryError,
    prepare_atomic_write_intent,
)


def leave_partial_atomic_intent(
    path: Path,
    content: bytes,
    *,
    intent_directory: Path,
) -> Path:
    intent = prepare_atomic_write_intent(
        path,
        content,
        intent_directory=intent_directory,
    )
    intent.scratch.write_bytes(content[: max(1, len(content) // 2)])
    intent.scratch.chmod(0o600)
    return intent.scratch


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


class InvalidResultExecutor:
    def execute(self, request: object) -> object:
        del request
        return ExecutionResult(
            executor_name="unexpected",
            changed_paths=("sentinel.txt",),
            observation="",
        )


class AliasArtifactBeforeFixtureExecution:
    def __init__(self, repository: Path, redirected: Path, alias_kind: str) -> None:
        self.repository = repository
        self.redirected = redirected
        self.alias_kind = alias_kind
        self.delegate = second_mate.FixtureExecutor()

    def execute(self, request: object) -> object:
        artifact = self.repository / "artifact.txt"
        artifact.unlink()
        if self.alias_kind == "symlink":
            artifact.symlink_to(self.redirected.name)
        else:
            os.link(self.redirected, artifact)
        return self.delegate.execute(request)


class RetargetRepositoryAliasBeforeFixtureExecution:
    def __init__(self, alias: Path, replacement: Path) -> None:
        self.alias = alias
        self.replacement = replacement
        self.delegate = second_mate.FixtureExecutor()

    def execute(self, request: object) -> object:
        self.alias.unlink()
        self.alias.symlink_to(self.replacement, target_is_directory=True)
        return self.delegate.execute(request)


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


def test_exact_start_retries_a_partial_first_state_write_before_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    grant = exact_grant(draft, basis)
    executor = CountingFixtureExecutor()

    def interrupt_first_state_write(
        writer: PosixAtomicWriter,
        path: Path,
        content: bytes,
        *,
        intent_directory: Path,
    ) -> None:
        del writer
        leave_partial_atomic_intent(
            path,
            content,
            intent_directory=intent_directory,
        )
        raise StateRecoveryError("simulated interruption during first state write")

    with monkeypatch.context() as context:
        context.setattr(PosixAtomicWriter, "write", interrupt_first_state_write)
        with pytest.raises(StateRecoveryError, match="first state write"):
            second_mate.start_run(
                draft=draft,
                basis=basis,
                grant_data=grant,
                repository=repository,
                executor=executor,
                owner_id="owner-1",
            )

    assert executor.invocation_count == 0
    assert (repository / "artifact.txt").read_text(encoding="utf-8") == "before\n"
    assert not (repository / ".second-mate" / "state.json").exists()

    recovered = second_mate.start_run(
        draft=draft,
        basis=basis,
        grant_data=grant,
        repository=repository,
        executor=executor,
        owner_id="owner-1",
    )

    assert executor.invocation_count == 1
    assert recovered.run.phase == "awaiting_evidence"
    assert (repository / "artifact.txt").read_text(encoding="utf-8") == "after\n"


def test_durable_active_state_requires_restart_if_marker_retirement_was_interrupted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    grant = exact_grant(draft, basis)
    executor = CountingFixtureExecutor()
    original_delete = store_module._delete_atomic_intent
    interrupted = False

    def interrupt_first_marker_retirement(intent: AtomicWriteIntent) -> None:
        nonlocal interrupted
        if not interrupted:
            interrupted = True
            raise StateRecoveryError("simulated interruption after durable owner state")
        original_delete(intent)

    with monkeypatch.context() as context:
        context.setattr(
            "second_mate.store._delete_atomic_intent",
            interrupt_first_marker_retirement,
        )
        with pytest.raises(StateRecoveryError, match="durable owner state"):
            second_mate.start_run(
                draft=draft,
                basis=basis,
                grant_data=grant,
                repository=repository,
                executor=executor,
                owner_id="owner-1",
            )

    assert executor.invocation_count == 0
    assert second_mate.load_state(repository).run.phase == "active"
    with pytest.raises(second_mate.RunConflictError, match="already exists"):
        second_mate.start_run(
            draft=draft,
            basis=basis,
            grant_data=grant,
            repository=repository,
            executor=executor,
            owner_id="owner-1",
        )

    recovered = second_mate.restart_run(repository, executor, owner_id="owner-1")

    assert executor.invocation_count == 1
    assert recovered.run.phase == "awaiting_evidence"
    assert (repository / "artifact.txt").read_text(encoding="utf-8") == "after\n"


def test_restart_reconciles_after_mutation_when_final_state_write_was_partial(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    grant = exact_grant(draft, basis)
    executor = CountingFixtureExecutor()
    original_write = PosixAtomicWriter.write
    state_writes = 0

    def interrupt_second_state_write(
        writer: PosixAtomicWriter,
        path: Path,
        content: bytes,
        *,
        intent_directory: Path,
    ) -> None:
        nonlocal state_writes
        if path.name == "state.json":
            state_writes += 1
            if state_writes == 2:
                leave_partial_atomic_intent(
                    path,
                    content,
                    intent_directory=intent_directory,
                )
                raise StateRecoveryError("simulated interruption after fixture mutation")
        original_write(writer, path, content, intent_directory=intent_directory)

    with monkeypatch.context() as context:
        context.setattr(PosixAtomicWriter, "write", interrupt_second_state_write)
        with pytest.raises(StateRecoveryError, match="after fixture mutation"):
            second_mate.start_run(
                draft=draft,
                basis=basis,
                grant_data=grant,
                repository=repository,
                executor=executor,
                owner_id="owner-1",
            )

    assert executor.invocation_count == 1
    assert second_mate.load_state(repository).run.phase == "active"
    duplicate = CountingFixtureExecutor()

    recovered = second_mate.restart_run(repository, duplicate, owner_id="owner-1")

    assert duplicate.invocation_count == 0
    assert recovered.run.phase == "awaiting_evidence"
    assert not tuple((repository / ".second-mate").glob("state.json.next.*"))


def test_invalid_executor_results_become_readable_packet_failures_on_start_and_restart(
    tmp_path: Path,
) -> None:
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    executor = InvalidResultExecutor()

    with pytest.raises(second_mate.ExecutionFailure, match="dispatch failed"):
        second_mate.start_run(
            draft=draft,
            basis=basis,
            grant_data=exact_grant(draft, basis),
            repository=repository,
            executor=executor,
            owner_id="owner-1",
        )

    first = second_mate.load_state(repository)
    assert first.run.phase == "failed"
    assert first.run.executor_result is None
    with pytest.raises(second_mate.ExecutionFailure, match="dispatch failed"):
        second_mate.restart_run(repository, executor, owner_id="owner-1")
    second = second_mate.load_state(repository)
    assert second.run.phase == "failed"
    assert second.run.attempts == 2
    assert second.run.executor_result is None


@pytest.mark.parametrize("alias_kind", ("symlink", "hardlink"))
def test_fixture_executor_refuses_a_path_alias_before_writing_outside_the_grant(
    tmp_path: Path,
    alias_kind: str,
) -> None:
    """A late path alias must fail before the redirected file is written."""
    repository = make_repository(tmp_path)
    redirected = repository / "redirected.txt"
    redirected.write_text("before\n", encoding="utf-8")
    run_git(repository, "add", "redirected.txt")
    run_git(repository, "commit", "-q", "-m", "add out-of-boundary redirect target")
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)

    with pytest.raises(second_mate.ExecutionFailure, match="dispatch failed"):
        second_mate.start_run(
            draft=draft,
            basis=basis,
            grant_data=exact_grant(draft, basis),
            repository=repository,
            executor=AliasArtifactBeforeFixtureExecution(repository, redirected, alias_kind),
            owner_id="owner-1",
        )

    assert redirected.read_text(encoding="utf-8") == "before\n"
    assert os.path.samefile(repository / "artifact.txt", redirected)
    state = second_mate.load_state(repository)
    assert state.run.phase == "failed"
    assert state.recovery_pressure == "packet"


def test_late_target_alias_retarget_cannot_move_dispatch_to_an_identical_clone(
    tmp_path: Path,
) -> None:
    repository = make_repository(tmp_path)
    clone = tmp_path / "clone"
    shutil.copytree(repository, clone)
    alias = tmp_path / "target-alias"
    alias.symlink_to(repository, target_is_directory=True)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, alias)

    state = second_mate.start_run(
        draft=draft,
        basis=basis,
        grant_data=exact_grant(draft, basis),
        repository=alias,
        executor=RetargetRepositoryAliasBeforeFixtureExecution(alias, clone),
        owner_id="owner-1",
    )

    assert alias.resolve() == clone.resolve()
    assert (repository / "artifact.txt").read_text(encoding="utf-8") == "after\n"
    assert (clone / "artifact.txt").read_text(encoding="utf-8") == "before\n"
    assert state.run.phase == "awaiting_evidence"
    assert second_mate.load_state(repository).run.phase == "awaiting_evidence"
    assert not (clone / ".second-mate").exists()


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


@pytest.mark.parametrize(
    "field_path",
    (
        ("schema_version",),
        ("preflight", "schema_version"),
        ("preflight", "preflight", "schema_version"),
    ),
)
def test_load_state_explicitly_rejects_legacy_v1_durable_formats(
    tmp_path: Path,
    field_path: tuple[str, ...],
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
    owner[field_path[-1]] = 1
    state_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    before = state_path.read_bytes()

    with pytest.raises(second_mate.ValidationError, match="schema"):
        second_mate.load_state(repository)

    assert state_path.read_bytes() == before


@pytest.mark.parametrize(
    "contradiction",
    (
        "failed-baseline",
        "eligible-with-failures",
        "irreversible",
        "proof-path",
        "dependency-state",
    ),
)
def test_load_state_rejects_impossible_persisted_preflight_semantics(
    tmp_path: Path,
    contradiction: str,
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
    envelope = document["preflight"]
    record = envelope["preflight"]
    if contradiction == "failed-baseline":
        record["affected_baseline"]["result"] = "fail"
    elif contradiction == "eligible-with-failures":
        record["existing_failures"] = ["forged pre-existing failure"]
    elif contradiction == "irreversible":
        record["irreversible_change"]["required"] = True
    elif contradiction == "proof-path":
        record["affected_baseline"]["artifact_path"] = "sentinel.txt"
    else:
        record["dependency_state"] = []
    envelope["preflight_digest"] = digest_json(record)
    document["grant"]["preflight_digest"] = envelope["preflight_digest"]
    state_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    before = state_path.read_bytes()

    with pytest.raises(second_mate.ValidationError, match=r"preflight|baseline|dependency"):
        second_mate.load_state(repository)

    assert state_path.read_bytes() == before


@pytest.mark.parametrize(
    ("field_path", "invalid_value"),
    (
        (("closed",), True),
        (("route_status",), "completed"),
        (("run", "phase"), "closed"),
    ),
)
def test_load_state_rejects_inconsistent_closed_markers(
    tmp_path: Path,
    field_path: tuple[str, ...],
    invalid_value: object,
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
    owner[field_path[-1]] = invalid_value
    state_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    before = state_path.read_bytes()

    with pytest.raises(second_mate.ValidationError, match="closed status is inconsistent"):
        second_mate.load_state(repository)

    assert state_path.read_bytes() == before


@pytest.mark.parametrize(
    ("field_path", "invalid_value"),
    (
        (("run", "phase"), "invented"),
        (("route_status",), "invented"),
        (("direction_coverage",), "invented"),
        (("recovery_pressure",), "invented"),
        (("run", "owner_id"), ""),
        (("run", "recovery_action"), ""),
        (("handoff",), ""),
    ),
)
def test_load_state_rejects_unknown_lifecycle_values_and_empty_continuation(
    tmp_path: Path,
    field_path: tuple[str, ...],
    invalid_value: object,
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
    owner[field_path[-1]] = invalid_value
    state_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    before = state_path.read_bytes()

    with pytest.raises(second_mate.ValidationError, match="state"):
        second_mate.load_state(repository)

    assert state_path.read_bytes() == before


@pytest.mark.parametrize(
    "changes",
    (
        ((("run", "executor_result"), None),),
        ((("run", "phase"), "ready_to_close"),),
        ((("run", "phase"), "evidence_failed"), (("recovery_pressure",), "packet")),
        ((("run", "phase"), "active"),),
        ((("recovery_pressure",), "packet"),),
    ),
)
def test_load_state_rejects_inconsistent_phase_result_evidence_and_pressure(
    tmp_path: Path,
    changes: tuple[tuple[tuple[str, ...], object], ...],
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
    for field_path, invalid_value in changes:
        owner = document
        for field in field_path[:-1]:
            owner = owner[field]
            assert isinstance(owner, dict)
        owner[field_path[-1]] = invalid_value
    state_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    before = state_path.read_bytes()

    with pytest.raises(second_mate.ValidationError, match="lifecycle is inconsistent"):
        second_mate.load_state(repository)

    assert state_path.read_bytes() == before


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    (
        ("executor_name", "invented"),
        ("changed_paths", ["sentinel.txt"]),
        ("observation", ""),
    ),
)
def test_load_state_rejects_an_invalid_fixture_executor_result(
    tmp_path: Path,
    field: str,
    invalid_value: object,
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
    document["run"]["executor_result"][field] = invalid_value
    state_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    before = state_path.read_bytes()

    with pytest.raises(second_mate.ValidationError, match="executor result"):
        second_mate.load_state(repository)

    assert state_path.read_bytes() == before


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


def test_copied_durable_state_cannot_authorize_restart_in_an_identical_clone(
    tmp_path: Path,
) -> None:
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    with pytest.raises(second_mate.ExecutionFailure):
        second_mate.start_run(
            draft=draft,
            basis=basis,
            grant_data=exact_grant(draft, basis),
            repository=repository,
            executor=FailOnceFixtureExecutor(),
            owner_id="owner-1",
        )
    clone = tmp_path / "clone"
    shutil.copytree(repository, clone)
    clone_state = clone / ".second-mate" / "state.json"
    state_before = clone_state.read_bytes()
    executor = CountingFixtureExecutor()

    with pytest.raises(second_mate.AuthorityError, match="target"):
        second_mate.restart_run(clone, executor, owner_id="owner-1")

    assert executor.invocation_count == 0
    assert (clone / "artifact.txt").read_text(encoding="utf-8") == "before\n"
    assert clone_state.read_bytes() == state_before


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
    git_lock = Path(run_git(repository, "rev-parse", "--git-path", "second-mate-fs01.lock"))
    if not git_lock.is_absolute():
        git_lock = repository / git_lock
    git_lock.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(git_lock, os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with pytest.raises(second_mate.RunConflictError, match="lock"):
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


@pytest.mark.parametrize("alias_kind", ("symlink", "hardlink"))
def test_run_lock_refuses_filesystem_aliases_before_dispatch(
    tmp_path: Path,
    alias_kind: str,
) -> None:
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    lock_path = Path(run_git(repository, "rev-parse", "--git-path", "second-mate-fs01.lock"))
    if not lock_path.is_absolute():
        lock_path = repository / lock_path
    external = tmp_path / "external-lock"
    external.write_text("external lock content\n", encoding="utf-8")
    if alias_kind == "symlink":
        lock_path.symlink_to(external)
    else:
        os.link(external, lock_path)
    executor = CountingFixtureExecutor()

    with pytest.raises(second_mate.RunConflictError, match="unsafe"):
        second_mate.start_run(
            draft=draft,
            basis=basis,
            grant_data=exact_grant(draft, basis),
            repository=repository,
            executor=executor,
            owner_id="owner-1",
        )

    assert executor.invocation_count == 0
    assert external.read_text(encoding="utf-8") == "external lock content\n"
    assert (repository / "artifact.txt").read_text(encoding="utf-8") == "before\n"
    assert not (repository / ".second-mate").exists()


@pytest.mark.parametrize("operation", ("evidence", "close"))
def test_run_lock_serializes_every_durable_lifecycle_mutation(
    tmp_path: Path,
    operation: str,
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
    if operation == "close":
        second_mate.record_evidence(repository)
    state_path = repository / ".second-mate" / "state.json"
    before = state_path.read_bytes()
    git_lock = Path(run_git(repository, "rev-parse", "--git-path", "second-mate-fs01.lock"))
    if not git_lock.is_absolute():
        git_lock = repository / git_lock
    git_lock.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(git_lock, os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with pytest.raises(second_mate.RunConflictError, match="lock"):
            if operation == "evidence":
                second_mate.record_evidence(repository)
            else:
                second_mate.clean_close(
                    repository,
                    direction_coverage="still_remaining",
                    residual_uncertainty=(
                        "Live provider behavior was not exercised.",
                        "Human product review remains outstanding.",
                    ),
                    handoff="FS-01 close must wait for the lifecycle lock.",
                )
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)

    assert state_path.read_bytes() == before
