from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from typing import Any

import pytest
from test_authority import exact_grant
from test_draft import valid_direction as fs01_direction
from test_draft import valid_packet
from test_preflight import make_repository, run_git, target_snapshot

import second_mate
import second_mate.direction as direction_module
from second_mate.repository import git_private_path, inspect_revision
from second_mate.store import PosixAtomicWriter, prepare_atomic_write_intent, strict_json_loads


def exact_approval(candidate: object, *, suffix: str = "1") -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": f"direction-approval-{suffix}",
        "decision": "approved",
        "direction_id": candidate.candidate.id,
        "candidate_digest": candidate.digest,
        "approved_by": "project-owner",
        "approved_at": f"2026-08-04T10:0{suffix}:00Z",
    }


def exact_promotion_grant(candidate: object, *, suffix: str = "1") -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": f"direction-promotion-{suffix}",
        "granted_by": "project-owner",
        "granted_at": f"2026-08-04T10:1{suffix}:00Z",
        "candidate_digest": candidate.digest,
        "target_head": candidate.promotion_basis.target_head,
        "target_fingerprint": candidate.promotion_basis.target_fingerprint,
        "run_state_sha256": candidate.promotion_basis.run_state_sha256,
        "allowed_paths": [".second-mate/directions.json"],
        "allowed_effects": ["direction_ledger_write"],
        "stop_conditions": ["revision_drift", "direction_history_drift", "open_run"],
    }


def test_prepare_direction_is_read_only_and_freezes_portable_exact_text(tmp_path: Path) -> None:
    """Writing during preparation or persisting a checkout path must break this contract."""
    repository = make_repository(tmp_path)
    before = target_snapshot(repository)
    assert hasattr(second_mate, "prepare_direction")

    candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )

    assert candidate.to_json() == {
        "candidate": {
            "change_note": None,
            "id": "D-01",
            "schema_version": 1,
            "supersedes": None,
            "text": "Keep authority explicit.\n",
        },
        "candidate_digest": "9a37c2b50e07a75d3afc95a97205b4af0e413c9a39b6bdea7fb9bb354b9eea26",
        "promotion_basis": {
            "run_state_sha256": None,
            "target_fingerprint": inspect_revision(repository).fingerprint,
            "target_head": inspect_revision(repository).head,
        },
        "schema_version": 1,
    }
    assert str(repository) not in repr(candidate.to_json())
    assert target_snapshot(repository) == before
    assert not (repository / ".second-mate").exists()


def test_promote_requires_separate_approval_and_write_grant_then_feeds_draft(
    tmp_path: Path,
) -> None:
    """Conflating approval with promotion or storing a non-draft Direction must fail."""
    repository = make_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    assert hasattr(second_mate, "promote_direction")

    version = second_mate.promote_direction(
        repository,
        candidate.to_json(),
        exact_approval(candidate),
        exact_promotion_grant(candidate),
    )

    approved_direction: dict[str, Any] = {
        "approval": {
            "approved_at": "2026-08-04T10:01:00Z",
            "approved_by": "project-owner",
        },
        "id": "D-01",
        "schema_version": 1,
        "text": "Keep authority explicit.\n",
    }
    assert version.direction.to_json() == approved_direction
    packet = valid_packet()
    packet["outcome"] = "Safely consume the approved Direction."
    assert second_mate.create_draft(approved_direction, packet).direction.id == "D-01"

    ledger_path = repository / ".second-mate" / "directions.json"
    ledger = strict_json_loads(ledger_path.read_bytes())
    assert isinstance(ledger, dict)
    assert ledger["current_direction_id"] == "D-01"
    assert len(ledger["versions"]) == 1
    assert str(repository) not in ledger_path.read_text(encoding="utf-8")
    assert [
        item.path
        for item in inspect_revision(repository).files
        if item.path.startswith(".second-mate/")
    ] == [".second-mate/directions.json"]


def test_material_change_appends_an_exact_linear_version_and_preserves_d01(tmp_path: Path) -> None:
    """Overwriting D-01 or accepting a branch instead of D-01 -> D-02 must fail."""
    repository = make_repository(tmp_path)
    d01_candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    d01 = second_mate.promote_direction(
        repository,
        d01_candidate.to_json(),
        exact_approval(d01_candidate),
        exact_promotion_grant(d01_candidate),
    )
    original_bytes = (repository / ".second-mate" / "directions.json").read_bytes()

    d02_candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit and preserve exact evidence.\n",
        direction_id="D-02",
        change_note="Add the evidence boundary requested by the owner.",
    )

    assert d02_candidate.candidate.supersedes is not None
    assert d02_candidate.candidate.supersedes.direction_id == "D-01"
    assert d02_candidate.candidate.supersedes.direction_digest == d01.direction_digest
    d02 = second_mate.promote_direction(
        repository,
        d02_candidate.to_json(),
        exact_approval(d02_candidate, suffix="2"),
        exact_promotion_grant(d02_candidate, suffix="2"),
    )

    assert second_mate.load_direction(repository).to_json() == d02.direction.to_json()
    assert second_mate.load_direction(repository, "D-01").to_json() == d01.direction.to_json()
    ledger = strict_json_loads((repository / ".second-mate" / "directions.json").read_bytes())
    assert isinstance(ledger, dict)
    assert [item["direction"]["id"] for item in ledger["versions"]] == ["D-01", "D-02"]
    assert ledger["versions"][0] == strict_json_loads(original_bytes)["versions"][0]
    assert str(repository) not in repr(ledger)


def test_open_packet_run_blocks_direction_promotion_without_changing_history(
    tmp_path: Path,
) -> None:
    """Removing the open-run guard must let product meaning change during execution."""
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(fs01_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    second_mate.start_run(
        draft=draft,
        basis=basis,
        grant_data=exact_grant(draft, basis),
        repository=repository,
        executor=second_mate.FixtureExecutor(),
        owner_id="owner-1",
    )
    candidate = second_mate.prepare_direction(
        repository,
        "Do not change meaning during an open run.\n",
        direction_id="D-01",
        change_note=None,
    )
    before = target_snapshot(repository)

    with pytest.raises(second_mate.DirectionConflictError, match="open packet run"):
        second_mate.promote_direction(
            repository,
            candidate.to_json(),
            exact_approval(candidate),
            exact_promotion_grant(candidate),
        )

    assert target_snapshot(repository) == before
    assert not (repository / ".second-mate" / "directions.json").exists()


def test_prepare_refuses_ignored_direction_history_path_without_writing(tmp_path: Path) -> None:
    """Removing the ignore check must allow approved history to vanish from cloneable state."""
    repository = make_repository(tmp_path)
    (repository / ".gitignore").write_text(".second-mate/\n", encoding="utf-8")
    run_git(repository, "add", ".gitignore")
    run_git(repository, "commit", "-q", "-m", "ignore coordinator state")
    before = target_snapshot(repository)

    with pytest.raises(second_mate.ValidationError, match="must not be ignored"):
        second_mate.prepare_direction(
            repository,
            "This must remain clone-readable.\n",
            direction_id="D-01",
            change_note=None,
        )

    assert target_snapshot(repository) == before
    assert not (repository / ".second-mate").exists()


def test_prepare_refuses_missing_git_recorded_history_instead_of_restarting(tmp_path: Path) -> None:
    """Treating deleted tracked history as a fresh D-01 must fork repository authority."""
    repository = make_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    second_mate.promote_direction(
        repository,
        candidate.to_json(),
        exact_approval(candidate),
        exact_promotion_grant(candidate),
    )
    run_git(repository, "add", ".second-mate/directions.json")
    run_git(repository, "commit", "-q", "-m", "record approved Direction")
    (repository / ".second-mate" / "directions.json").unlink()
    before = target_snapshot(repository)

    with pytest.raises(second_mate.DirectionConflictError, match="recorded by Git but missing"):
        second_mate.prepare_direction(
            repository,
            "A replacement must not restart history.\n",
            direction_id="D-01-replacement",
            change_note=None,
        )

    assert target_snapshot(repository) == before


@pytest.mark.parametrize("missing_record", ("approval", "promotion_grant"))
def test_promotion_requires_both_authority_records_without_writing(
    tmp_path: Path,
    missing_record: str,
) -> None:
    repository = make_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Both authority records are required.\n",
        direction_id="D-01",
        change_note=None,
    )
    approval = None if missing_record == "approval" else exact_approval(candidate)
    grant = None if missing_record == "promotion_grant" else exact_promotion_grant(candidate)
    before = target_snapshot(repository)

    with pytest.raises(second_mate.ValidationError, match="explicit Direction"):
        second_mate.promote_direction(repository, candidate.to_json(), approval, grant)

    assert target_snapshot(repository) == before
    assert not (repository / ".second-mate").exists()


def test_revision_drift_invalidates_prepared_promotion_without_overwriting_drift(
    tmp_path: Path,
) -> None:
    repository = make_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Bind promotion to the exact repository basis.\n",
        direction_id="D-01",
        change_note=None,
    )
    (repository / "outside.txt").write_text("outside drift\n", encoding="utf-8")
    drifted = target_snapshot(repository)

    with pytest.raises(second_mate.DirectionConflictError, match="revision drift"):
        second_mate.promote_direction(
            repository,
            candidate.to_json(),
            exact_approval(candidate),
            exact_promotion_grant(candidate),
        )

    assert target_snapshot(repository) == drifted
    assert not (repository / ".second-mate").exists()


def test_direction_promotion_uses_the_shared_repository_mutation_lock(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Serialize every mutation.\n",
        direction_id="D-01",
        change_note=None,
    )
    lock_path = Path(run_git(repository, "rev-parse", "--git-path", "second-mate-mutation.lock"))
    if not lock_path.is_absolute():
        lock_path = repository / lock_path
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with pytest.raises(second_mate.DirectionConflictError, match="mutation lock"):
            second_mate.promote_direction(
                repository,
                candidate.to_json(),
                exact_approval(candidate),
                exact_promotion_grant(candidate),
            )
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)

    assert not (repository / ".second-mate").exists()


def test_racing_initial_promotions_create_one_history_without_overwrite(tmp_path: Path) -> None:
    """Removing shared coordination must let two initial versions both report success."""
    repository = make_repository(tmp_path)
    candidates = tuple(
        second_mate.prepare_direction(
            repository,
            f"Candidate {suffix}.\n",
            direction_id=f"D-0{suffix}",
            change_note=None,
        )
        for suffix in (1, 2)
    )
    barrier = Barrier(2)

    def promote(index: int) -> str:
        candidate = candidates[index]
        barrier.wait()
        try:
            version = second_mate.promote_direction(
                repository,
                candidate.to_json(),
                exact_approval(candidate, suffix=str(index + 1)),
                exact_promotion_grant(candidate, suffix=str(index + 1)),
            )
        except second_mate.DirectionConflictError:
            return "conflict"
        return version.direction.id

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(promote, (0, 1)))

    winners = [result for result in results if result != "conflict"]
    assert len(winners) == 1
    assert second_mate.load_direction(repository).id == winners[0]
    ledger = strict_json_loads((repository / ".second-mate" / "directions.json").read_bytes())
    assert isinstance(ledger, dict)
    assert len(ledger["versions"]) == 1


def test_cli_prepares_direction_without_mutating_target(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    summary = tmp_path / "direction.md"
    summary.write_text("Prepare this exact Direction.\n", encoding="utf-8")
    before = target_snapshot(repository)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "second_mate",
            "direction",
            "prepare",
            "--target",
            os.fspath(repository),
            "--summary",
            os.fspath(summary),
            "--id",
            "D-01",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    document = strict_json_loads(completed.stdout)
    assert isinstance(document, dict)
    assert document["candidate"]["text"] == "Prepare this exact Direction.\n"
    assert document["candidate"]["id"] == "D-01"
    assert target_snapshot(repository) == before


def test_exact_retry_recovers_a_durably_marked_partial_direction_write(tmp_path: Path) -> None:
    """Ignoring a coordinator-owned partial intent must make exact retry unrecoverable."""
    source_parent = tmp_path / "source-parent"
    target_parent = tmp_path / "target-parent"
    source_parent.mkdir()
    target_parent.mkdir()
    source = make_repository(source_parent)
    target = make_repository(target_parent)
    source_candidate = second_mate.prepare_direction(
        source,
        "Recover only the exact intended Direction.\n",
        direction_id="D-01",
        change_note=None,
    )
    target_candidate = second_mate.prepare_direction(
        target,
        "Recover only the exact intended Direction.\n",
        direction_id="D-01",
        change_note=None,
    )
    assert source_candidate.to_json() == target_candidate.to_json()
    second_mate.promote_direction(
        source,
        source_candidate.to_json(),
        exact_approval(source_candidate),
        exact_promotion_grant(source_candidate),
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

    second_mate.promote_direction(
        target,
        target_candidate.to_json(),
        exact_approval(target_candidate),
        exact_promotion_grant(target_candidate),
    )

    assert target_path.read_bytes() == intended
    assert not intent.scratch.exists()
    assert not intent.marker.exists()


def test_initial_promotion_never_overwrites_history_created_during_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replacing a late competing ledger must destroy immutable repository authority."""
    source_parent = tmp_path / "source-parent"
    target_parent = tmp_path / "target-parent"
    source_parent.mkdir()
    target_parent.mkdir()
    source = make_repository(source_parent)
    target = make_repository(target_parent)
    competing_candidate = second_mate.prepare_direction(
        source,
        "Competing approved history.\n",
        direction_id="D-COMPETING",
        change_note=None,
    )
    second_mate.promote_direction(
        source,
        competing_candidate.to_json(),
        exact_approval(competing_candidate),
        exact_promotion_grant(competing_candidate),
    )
    competing = (source / ".second-mate" / "directions.json").read_bytes()
    candidate = second_mate.prepare_direction(
        target,
        "Intended approved history.\n",
        direction_id="D-01",
        change_note=None,
    )
    original_create = PosixAtomicWriter.create

    def inject_competing_history(
        writer: PosixAtomicWriter,
        path: Path,
        content: bytes,
        *,
        intent_directory: Path,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(competing)
        original_create(writer, path, content, intent_directory=intent_directory)

    monkeypatch.setattr(direction_module.PosixAtomicWriter, "create", inject_competing_history)

    with pytest.raises(second_mate.DirectionConflictError, match="history appeared"):
        second_mate.promote_direction(
            target,
            candidate.to_json(),
            exact_approval(candidate),
            exact_promotion_grant(candidate),
        )

    assert (target / ".second-mate" / "directions.json").read_bytes() == competing


def test_changed_direction_restores_history_changed_during_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replacing a late D-01 change must erase authority that won the race."""
    repository = make_repository(tmp_path)
    d01_candidate = second_mate.prepare_direction(
        repository,
        "Initial Direction.\n",
        direction_id="D-01",
        change_note=None,
    )
    second_mate.promote_direction(
        repository,
        d01_candidate.to_json(),
        exact_approval(d01_candidate),
        exact_promotion_grant(d01_candidate),
    )
    d02_candidate = second_mate.prepare_direction(
        repository,
        "Changed Direction.\n",
        direction_id="D-02",
        change_note="Change the exact approved meaning.",
    )
    competing = b"late competing history\n"
    original_exchange = PosixAtomicWriter.exchange

    def inject_competing_history(
        writer: PosixAtomicWriter,
        path: Path,
        expected: bytes,
        content: bytes,
        *,
        intent_directory: Path,
    ) -> None:
        path.write_bytes(competing)
        original_exchange(
            writer,
            path,
            expected,
            content,
            intent_directory=intent_directory,
        )

    monkeypatch.setattr(direction_module.PosixAtomicWriter, "exchange", inject_competing_history)

    with pytest.raises(second_mate.DirectionConflictError, match="history changed"):
        second_mate.promote_direction(
            repository,
            d02_candidate.to_json(),
            exact_approval(d02_candidate, suffix="2"),
            exact_promotion_grant(d02_candidate, suffix="2"),
        )

    assert (repository / ".second-mate" / "directions.json").read_bytes() == competing


@pytest.mark.parametrize(
    "mismatch",
    (
        "approval_direction",
        "approval_digest",
        "grant_digest",
        "grant_fingerprint",
        "grant_boundary",
    ),
)
def test_approval_and_promotion_grant_bind_exact_candidate_basis_and_boundary(
    tmp_path: Path,
    mismatch: str,
) -> None:
    repository = make_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Bind both independent authority records exactly.\n",
        direction_id="D-01",
        change_note=None,
    )
    approval = exact_approval(candidate)
    grant = exact_promotion_grant(candidate)
    if mismatch == "approval_direction":
        approval["direction_id"] = "D-OTHER"
    elif mismatch == "approval_digest":
        approval["candidate_digest"] = "0" * 64
    elif mismatch == "grant_digest":
        grant["candidate_digest"] = "0" * 64
    elif mismatch == "grant_fingerprint":
        grant["target_fingerprint"] = "0" * 64
    else:
        grant["allowed_paths"] = [".second-mate/directions.json", "README.md"]
    before = target_snapshot(repository)

    with pytest.raises(second_mate.ValidationError):
        second_mate.promote_direction(repository, candidate.to_json(), approval, grant)

    assert target_snapshot(repository) == before
    assert not (repository / ".second-mate").exists()


def test_tampered_or_ambiguous_direction_history_is_never_returned(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Return only validated approved Direction.\n",
        direction_id="D-01",
        change_note=None,
    )
    second_mate.promote_direction(
        repository,
        candidate.to_json(),
        exact_approval(candidate),
        exact_promotion_grant(candidate),
    )
    ledger_path = repository / ".second-mate" / "directions.json"
    ledger = strict_json_loads(ledger_path.read_bytes())
    assert isinstance(ledger, dict)
    ledger["versions"][0]["direction"]["approval"]["approved_by"] = "intruder"
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(second_mate.ValidationError, match=r"digest|disagrees"):
        second_mate.load_direction(repository)

    original = (repository / ".second-mate" / "directions.json").read_text(encoding="utf-8")
    ambiguous = original.replace(
        '  "schema_version": 1,',
        '  "schema_version": 1,\n  "schema_version": 1,',
        1,
    )
    ledger_path.write_text(ambiguous, encoding="utf-8")
    with pytest.raises(second_mate.ValidationError, match="duplicate"):
        second_mate.load_direction(repository)


def test_direction_schema_two_field_error_names_the_actual_schema(tmp_path: Path) -> None:
    """Bridge approval corruption must not be diagnosed as legacy schema one."""
    repository = make_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Keep bridge authority exact.",
        direction_id="D-CB-diagnostic",
        change_note=None,
    )
    approval = exact_approval(candidate)
    approval["schema_version"] = 2
    approval["proposal_digest"] = "0" * 64
    second_mate.promote_direction(
        repository,
        candidate.to_json(),
        approval,
        exact_promotion_grant(candidate),
    )
    ledger_path = repository / ".second-mate" / "directions.json"
    ledger = strict_json_loads(ledger_path.read_bytes())
    assert isinstance(ledger, dict)
    ledger["versions"][0]["approval"]["unexpected"] = True
    ledger_path.write_text(json.dumps(ledger, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(
        second_mate.ValidationError,
        match="Direction approval fields do not match schema version 2",
    ):
        second_mate.load_direction(repository)


def test_closed_packet_run_allows_a_new_exactly_bound_direction_promotion(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(fs01_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    second_mate.start_run(
        draft=draft,
        basis=basis,
        grant_data=exact_grant(draft, basis),
        repository=repository,
        executor=second_mate.FixtureExecutor(),
        owner_id="owner-1",
    )
    second_mate.record_evidence(repository)
    second_mate.clean_close(
        repository,
        direction_coverage="still_remaining",
        residual_uncertainty=(
            "Human product review remains outstanding.",
            "Live provider behavior was not exercised.",
        ),
        handoff="The fixture route is closed before Direction changes.",
    )
    candidate = second_mate.prepare_direction(
        repository,
        "Promote only after the earlier run closes.\n",
        direction_id="D-01-next",
        change_note=None,
    )

    promoted = second_mate.promote_direction(
        repository,
        candidate.to_json(),
        exact_approval(candidate),
        exact_promotion_grant(candidate),
    )

    assert promoted.direction.id == "D-01-next"


def test_new_direction_history_invalidates_earlier_execution_preflight_and_grant(
    tmp_path: Path,
) -> None:
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(fs01_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    execution_grant = exact_grant(draft, basis)
    candidate = second_mate.prepare_direction(
        repository,
        "Any approved history changes the execution basis.\n",
        direction_id="D-01-next",
        change_note=None,
    )
    second_mate.promote_direction(
        repository,
        candidate.to_json(),
        exact_approval(candidate),
        exact_promotion_grant(candidate),
    )
    before = target_snapshot(repository)

    with pytest.raises(second_mate.AuthorityError, match="revision drift"):
        second_mate.start_run(
            draft=draft,
            basis=basis,
            grant_data=execution_grant,
            repository=repository,
            executor=second_mate.FixtureExecutor(),
            owner_id="owner-1",
        )

    assert target_snapshot(repository) == before
    assert not (repository / ".second-mate" / "state.json").exists()


def test_exact_retry_finishes_direction_append_interrupted_after_atomic_exchange(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Losing post-exchange recovery must leave a successfully installed D-02 unusable."""
    repository = make_repository(tmp_path)
    d01_candidate = second_mate.prepare_direction(
        repository,
        "Initial Direction.\n",
        direction_id="D-01",
        change_note=None,
    )
    second_mate.promote_direction(
        repository,
        d01_candidate.to_json(),
        exact_approval(d01_candidate),
        exact_promotion_grant(d01_candidate),
    )
    d02_candidate = second_mate.prepare_direction(
        repository,
        "Changed Direction with exact recovery.\n",
        direction_id="D-02",
        change_note="Prove recovery after the append exchange.",
    )
    approval = exact_approval(d02_candidate, suffix="2")
    grant = exact_promotion_grant(d02_candidate, suffix="2")
    original_exchange = PosixAtomicWriter._exchange_paths

    def interrupt_after_exchange(left: Path, right: Path) -> None:
        original_exchange(left, right)
        raise KeyboardInterrupt("simulated interruption after Direction exchange")

    monkeypatch.setattr(
        direction_module.PosixAtomicWriter,
        "_exchange_paths",
        staticmethod(interrupt_after_exchange),
    )
    with pytest.raises(KeyboardInterrupt, match="after Direction exchange"):
        second_mate.promote_direction(
            repository,
            d02_candidate.to_json(),
            approval,
            grant,
        )
    monkeypatch.setattr(
        direction_module.PosixAtomicWriter,
        "_exchange_paths",
        staticmethod(original_exchange),
    )

    recovered = second_mate.promote_direction(
        repository,
        d02_candidate.to_json(),
        approval,
        grant,
    )

    assert recovered.direction.id == "D-02"
    assert second_mate.load_direction(repository).id == "D-02"
    assert not tuple((repository / ".second-mate").glob("directions.json.next.*"))
