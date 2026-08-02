from __future__ import annotations

import copy
import json
import stat
import subprocess
import threading
from pathlib import Path
from typing import Any

import pytest
from test_authority import RecordingExecutor, exact_grant
from test_draft import valid_packet
from test_preflight import make_repository as make_fs01_repository

import second_mate
import second_mate.direction as direction_module
from second_mate.domain import digest_json
from second_mate.repository import inspect_revision
from second_mate.service import ExecutionResult


def _run_git(repository: Path, *args: str) -> str:
    completed = subprocess.run(
        [
            "git",
            "-c",
            "user.name=Direction Fixture",
            "-c",
            "user.email=direction@example.invalid",
            *args,
        ],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _make_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "target"
    repository.mkdir()
    (repository / "README.md").write_text("# Direction target\n", encoding="utf-8")
    _run_git(repository, "init", "-q")
    _run_git(repository, "add", ".")
    _run_git(repository, "commit", "-q", "-m", "direction fixture baseline")
    return repository


def _snapshot(repository: Path) -> tuple[str, dict[str, bytes]]:
    files = {
        path.relative_to(repository).as_posix(): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repository).parts
    }
    return _run_git(repository, "status", "--porcelain=v1"), files


def _approval(candidate: Any, *, approval_id: str = "DA-01") -> dict[str, object]:
    return {
        "approved_at": "2026-08-02T12:00:00Z",
        "approved_by": "fixture-human",
        "candidate_digest": candidate.digest,
        "decision": "approved",
        "direction_id": candidate.candidate.id,
        "id": approval_id,
        "schema_version": 1,
    }


def _promotion_grant(candidate: Any, *, grant_id: str = "DPG-01") -> dict[str, object]:
    basis = candidate.promotion_basis
    return {
        "allowed_effects": ["direction_ledger_write"],
        "allowed_paths": [".second-mate/directions.json"],
        "candidate_digest": candidate.digest,
        "granted_at": "2026-08-02T12:01:00Z",
        "granted_by": "fixture-human",
        "id": grant_id,
        "schema_version": 1,
        "stop_conditions": ["revision_drift", "direction_history_drift"],
        "target_fingerprint": basis.target_fingerprint,
        "target_head": basis.target_head,
        "target_root": basis.target_root,
    }


def test_prepare_direction_preserves_exact_summary_without_target_write(tmp_path: Path) -> None:
    """Any candidate preparation write or text normalization must break this test."""
    repository = _make_repository(tmp_path)
    before = _snapshot(repository)
    summary = "Keep human meaning explicit.\n\nDo not treat silence as approval.\n"

    candidate = second_mate.prepare_direction(
        repository,
        summary,
        direction_id="D-01",
        change_note=None,
    )

    assert candidate.candidate.text == summary
    assert candidate.candidate.id == "D-01"
    assert candidate.candidate.supersedes is None
    assert candidate.candidate.change_note is None
    assert len(candidate.digest) == 64
    assert _snapshot(repository) == before
    assert not (repository / ".second-mate").exists()


@pytest.mark.parametrize("invalid_kind", ["missing", "digest", "decision", "extra_field"])
def test_promotion_requires_literal_digest_bound_approval_before_write(
    tmp_path: Path, invalid_kind: str
) -> None:
    """Weakening any approval field must allow unapproved meaning into project state."""
    repository = _make_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Keep human meaning explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    approval: dict[str, object] | None = _approval(candidate)
    if invalid_kind == "missing":
        approval = None
    elif invalid_kind == "digest":
        approval["candidate_digest"] = "0" * 64
    elif invalid_kind == "decision":
        approval["decision"] = "pending"
    else:
        approval["private_reasoning"] = "FIXTURE_PRIVATE_REASONING"
    before = _snapshot(repository)

    with pytest.raises(second_mate.ValidationError):
        second_mate.promote_direction(
            repository,
            candidate.to_json(),
            approval,
            _promotion_grant(candidate),
        )

    assert _snapshot(repository) == before
    assert not (repository / ".second-mate").exists()


def test_exact_approval_persists_existing_direction_schema_deterministically(
    tmp_path: Path,
) -> None:
    """Dropping exact approval metadata or deterministic history must break handoff reload."""
    repository = _make_repository(tmp_path)
    summary = "Keep human meaning explicit.\n"
    candidate = second_mate.prepare_direction(
        repository,
        summary,
        direction_id="D-01",
        change_note=None,
    )

    promoted = second_mate.promote_direction(
        repository,
        candidate.to_json(),
        _approval(candidate),
        _promotion_grant(candidate),
    )

    expected_direction: dict[str, Any] = {
        "approval": {
            "approved_at": "2026-08-02T12:00:00Z",
            "approved_by": "fixture-human",
        },
        "id": "D-01",
        "schema_version": 1,
        "text": summary,
    }
    assert promoted.direction.to_json() == expected_direction
    assert second_mate.load_direction(repository).to_json() == expected_direction
    ledger_path = repository / ".second-mate" / "directions.json"
    ledger_bytes = ledger_path.read_bytes()
    ledger = json.loads(ledger_bytes)
    assert ledger["current_direction_id"] == "D-01"
    assert ledger["versions"][0]["direction"] == expected_direction
    assert ledger["versions"][0]["approval"]["decision"] == "approved"
    assert ledger["versions"][0]["approval"]["candidate_digest"] == candidate.digest
    assert ledger_bytes.endswith(b"\n")
    assert b"FIXTURE_PRIVATE_REASONING" not in ledger_bytes

    duplicate = copy.deepcopy(candidate.to_json())
    duplicate["candidate"]["text"] = "Changed after approval.\n"
    with pytest.raises(second_mate.ValidationError):
        second_mate.promote_direction(
            repository,
            duplicate,
            _approval(candidate),
            _promotion_grant(candidate),
        )
    assert ledger_path.read_bytes() == ledger_bytes


def test_changed_direction_appends_exact_version_and_rejects_stale_branch(
    tmp_path: Path,
) -> None:
    """Replacing history or accepting a stale predecessor must break version authority."""
    repository = _make_repository(tmp_path)
    first_candidate = second_mate.prepare_direction(
        repository,
        "Keep human meaning explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    first = second_mate.promote_direction(
        repository,
        first_candidate.to_json(),
        _approval(first_candidate),
        _promotion_grant(first_candidate),
    )
    ledger_path = repository / ".second-mate" / "directions.json"
    first_entry = json.loads(ledger_path.read_bytes())["versions"][0]

    second_candidate = second_mate.prepare_direction(
        repository,
        "Keep human meaning explicit and show rejected ideas as boundaries.\n",
        direction_id="D-02",
        change_note="Retain rejected ideas as visible boundaries.",
    )
    stale_candidate = second_mate.prepare_direction(
        repository,
        "A competing stale branch.\n",
        direction_id="D-STALE",
        change_note="Competing meaning prepared from D-01.",
    )
    assert second_candidate.candidate.supersedes is not None
    assert second_candidate.candidate.supersedes.direction_id == "D-01"
    assert second_candidate.candidate.supersedes.direction_digest == first.direction_digest

    second_mate.promote_direction(
        repository,
        second_candidate.to_json(),
        _approval(second_candidate, approval_id="DA-02"),
        _promotion_grant(second_candidate, grant_id="DPG-02"),
    )

    ledger = json.loads(ledger_path.read_bytes())
    assert ledger["current_direction_id"] == "D-02"
    assert ledger["versions"][0] == first_entry
    assert ledger["versions"][1]["supersedes"] == {
        "direction_digest": first.direction_digest,
        "direction_id": "D-01",
    }
    assert second_mate.load_direction(repository).id == "D-02"
    assert second_mate.load_direction(repository, "D-01").text == first.direction.text
    final_bytes = ledger_path.read_bytes()

    with pytest.raises(second_mate.DirectionConflictError, match="revision drift"):
        second_mate.promote_direction(
            repository,
            stale_candidate.to_json(),
            _approval(stale_candidate, approval_id="DA-STALE"),
            _promotion_grant(stale_candidate, grant_id="DPG-STALE"),
        )
    with pytest.raises(second_mate.ValidationError, match="change note"):
        second_mate.prepare_direction(
            repository,
            "A third version without an explanation.\n",
            direction_id="D-03",
            change_note=None,
        )
    third_candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit with a third approved refinement.\n",
        direction_id="D-03",
        change_note="Add a third approved refinement.",
    )
    with pytest.raises(second_mate.DirectionConflictError, match="promotion grant id"):
        second_mate.promote_direction(
            repository,
            third_candidate.to_json(),
            _approval(third_candidate, approval_id="DA-03"),
            _promotion_grant(third_candidate, grant_id="DPG-02"),
        )
    assert ledger_path.read_bytes() == final_bytes


def test_ledger_rejects_approval_identity_that_disagrees_with_direction(tmp_path: Path) -> None:
    """Recomputing one digest must not let displayed approver identity contradict approval."""
    repository = _make_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Keep human meaning explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    second_mate.promote_direction(
        repository,
        candidate.to_json(),
        _approval(candidate),
        _promotion_grant(candidate),
    )
    ledger_path = repository / ".second-mate" / "directions.json"
    ledger = json.loads(ledger_path.read_bytes())
    version = ledger["versions"][0]
    version["direction"]["approval"]["approved_by"] = "forged-human"
    version["direction_digest"] = digest_json(version["direction"])
    ledger_path.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(second_mate.ValidationError, match="approval record"):
        second_mate.load_direction(repository)


def test_direction_approval_alone_cannot_authorize_project_write(tmp_path: Path) -> None:
    """Removing distinct promotion authority must let meaning approval authorize mutation."""
    repository = _make_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Keep human meaning explicit.\n",
        direction_id="D-01",
        change_note=None,
    )

    with pytest.raises(second_mate.ValidationError, match="promotion authority"):
        second_mate.promote_direction(
            repository,
            candidate.to_json(),
            _approval(candidate),
            None,
        )

    assert not (repository / ".second-mate").exists()


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("allowed_paths", [".second-mate/directions.json", "README.md"]),
        ("allowed_effects", ["direction_ledger_write", "arbitrary_project_write"]),
        ("stop_conditions", ["revision_drift"]),
    ],
)
def test_promotion_grant_cannot_broaden_or_drop_its_fixed_boundary(
    tmp_path: Path,
    field: str,
    invalid_value: list[str],
) -> None:
    """Weakening fixed path, effect, or stop conditions must authorize excess mutation."""
    repository = _make_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Keep human meaning explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    grant = _promotion_grant(candidate)
    grant[field] = invalid_value
    before = _snapshot(repository)

    with pytest.raises(second_mate.ValidationError, match="fixed boundary"):
        second_mate.promote_direction(
            repository,
            candidate.to_json(),
            _approval(candidate),
            grant,
        )

    assert _snapshot(repository) == before
    assert not (repository / ".second-mate").exists()


def test_promotion_authority_is_bound_to_exact_target_and_revision(tmp_path: Path) -> None:
    """Replaying one promotion grant across targets or target drift must never write."""
    repository = _make_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Keep human meaning explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    other_parent = tmp_path / "other"
    other_parent.mkdir()
    other_repository = _make_repository(other_parent)

    with pytest.raises(second_mate.ValidationError, match="different target"):
        second_mate.promote_direction(
            other_repository,
            candidate.to_json(),
            _approval(candidate),
            _promotion_grant(candidate),
        )
    assert not (other_repository / ".second-mate").exists()

    (repository / "README.md").write_text("Target changed after grant.\n", encoding="utf-8")
    with pytest.raises(second_mate.DirectionConflictError, match="revision drift"):
        second_mate.promote_direction(
            repository,
            candidate.to_json(),
            _approval(candidate),
            _promotion_grant(candidate),
        )
    assert not (repository / ".second-mate").exists()


class _BlockingExecutor:
    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()

    def execute(self, request: object) -> ExecutionResult:
        self.entered.set()
        if not self.release.wait(timeout=5):
            raise RuntimeError("blocking executor was not released")
        return ExecutionResult(
            executor_name="blocking-fixture",
            changed_paths=(),
            observation="dispatch released without mutation",
        )


def test_direction_promotion_cannot_race_authorized_executor_dispatch(tmp_path: Path) -> None:
    """Separate mutation locks must let new Direction authority race stale execution."""
    repository = make_fs01_repository(tmp_path)
    first_candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    first = second_mate.promote_direction(
        repository,
        first_candidate.to_json(),
        _approval(first_candidate),
        _promotion_grant(first_candidate),
    )
    draft = second_mate.create_draft(first.direction.to_json(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    executor = _BlockingExecutor()
    errors: list[BaseException] = []

    def dispatch() -> None:
        try:
            second_mate.start_run(
                draft=draft,
                basis=basis,
                grant_data=exact_grant(draft, basis),
                repository=repository,
                executor=executor,
                owner_id="blocking-owner",
            )
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=dispatch)
    thread.start()
    assert executor.entered.wait(timeout=5)
    second_candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit and retain rejected boundaries.\n",
        direction_id="D-02",
        change_note="Retain rejected boundaries.",
    )
    try:
        with pytest.raises(second_mate.DirectionConflictError, match="mutation boundary"):
            second_mate.promote_direction(
                repository,
                second_candidate.to_json(),
                _approval(second_candidate, approval_id="DA-02"),
                _promotion_grant(second_candidate, grant_id="DPG-02"),
            )
    finally:
        executor.release.set()
        thread.join(timeout=5)

    assert not thread.is_alive()
    assert errors == []
    assert second_mate.load_direction(repository).id == "D-01"


def test_direction_promotion_refuses_while_durable_packet_run_is_open(tmp_path: Path) -> None:
    """Releasing the process lock must not let Direction change under an open packet."""
    repository = make_fs01_repository(tmp_path)
    first_candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    first = second_mate.promote_direction(
        repository,
        first_candidate.to_json(),
        _approval(first_candidate),
        _promotion_grant(first_candidate),
    )
    draft = second_mate.create_draft(first.direction.to_json(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    second_mate.start_run(
        draft=draft,
        basis=basis,
        grant_data=exact_grant(draft, basis),
        repository=repository,
        executor=second_mate.FixtureExecutor(),
        owner_id="open-owner",
    )
    second_candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit and retain rejected boundaries.\n",
        direction_id="D-02",
        change_note="Retain rejected boundaries.",
    )

    with pytest.raises(second_mate.DirectionConflictError, match="open packet run"):
        second_mate.promote_direction(
            repository,
            second_candidate.to_json(),
            _approval(second_candidate, approval_id="DA-02"),
            _promotion_grant(second_candidate, grant_id="DPG-02"),
        )

    assert second_mate.load_direction(repository).id == "D-01"


def test_direction_promotion_rejects_symlinked_state_directory_at_write_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Following the state directory must let promotion write outside the target."""
    repository = _make_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    outside = tmp_path / "outside"
    outside.mkdir()
    (repository / ".second-mate").symlink_to(outside, target_is_directory=True)
    revision = inspect_revision(repository)
    candidate_data = candidate.to_json()
    promotion_basis = candidate_data["promotion_basis"]
    assert isinstance(promotion_basis, dict)
    promotion_basis["target_head"] = revision.head
    promotion_basis["target_fingerprint"] = revision.fingerprint
    grant = _promotion_grant(candidate)
    grant["target_head"] = revision.head
    grant["target_fingerprint"] = revision.fingerprint
    monkeypatch.setattr(direction_module, "repository_path_is_ignored", lambda *_: False)

    with pytest.raises(second_mate.ValidationError, match="symlink"):
        second_mate.promote_direction(
            repository,
            candidate_data,
            _approval(candidate),
            grant,
        )

    assert not (outside / "directions.json").exists()


def test_direction_promotion_rejects_actual_temporary_symlink_without_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dropping exclusive no-follow creation must overwrite the chosen outside target."""
    repository = _make_repository(tmp_path)
    state_directory = repository / ".second-mate"
    state_directory.mkdir()
    victim = tmp_path / "outside-victim.txt"
    victim.write_text("outside bytes must remain\n", encoding="utf-8")
    token = "ab" * 12
    temporary = state_directory / f".directions.json.{token}.next"
    temporary.symlink_to(victim)
    monkeypatch.setattr(direction_module.secrets, "token_hex", lambda _size: token)
    candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )

    with pytest.raises(second_mate.DirectionConflictError, match="temporary"):
        second_mate.promote_direction(
            repository,
            candidate.to_json(),
            _approval(candidate),
            _promotion_grant(candidate),
        )

    assert victim.read_text(encoding="utf-8") == "outside bytes must remain\n"
    assert not (state_directory / "directions.json").exists()


def test_direction_promotion_rejects_symlinked_final_ledger_without_outside_write(
    tmp_path: Path,
) -> None:
    """Following a final-ledger symlink must treat outside history as project authority."""
    source_parent = tmp_path / "source"
    source_parent.mkdir()
    source = _make_repository(source_parent)
    source_candidate = second_mate.prepare_direction(
        source,
        "Outside bytes must remain exact.\n",
        direction_id="D-OUTSIDE",
        change_note=None,
    )
    second_mate.promote_direction(
        source,
        source_candidate.to_json(),
        _approval(source_candidate, approval_id="DA-OUTSIDE"),
        _promotion_grant(source_candidate, grant_id="DPG-OUTSIDE"),
    )
    victim = source / ".second-mate" / "directions.json"
    victim_bytes = victim.read_bytes()

    repository = _make_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    state_directory = repository / ".second-mate"
    state_directory.mkdir()
    (state_directory / "directions.json").symlink_to(victim)
    revision = inspect_revision(repository)
    candidate_data = candidate.to_json()
    promotion_basis = candidate_data["promotion_basis"]
    assert isinstance(promotion_basis, dict)
    promotion_basis["target_head"] = revision.head
    promotion_basis["target_fingerprint"] = revision.fingerprint
    grant = _promotion_grant(candidate)
    grant["target_head"] = revision.head
    grant["target_fingerprint"] = revision.fingerprint

    with pytest.raises(second_mate.ValidationError, match="symlink"):
        second_mate.promote_direction(
            repository,
            candidate_data,
            _approval(candidate),
            grant,
        )

    assert victim.read_bytes() == victim_bytes
    assert (state_directory / "directions.json").is_symlink()


def test_direction_promotion_refuses_detached_state_directory_before_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Trusting only an open directory fd must let a rename redirect the final ledger."""
    repository = _make_repository(tmp_path)
    state_directory = repository / ".second-mate"
    state_directory.mkdir()
    candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    detached = tmp_path / "detached-state"
    original_write_temporary = direction_module._DirectionLedgerStore._write_temporary

    def write_then_detach(state_descriptor: int, content: bytes) -> str:
        temporary = original_write_temporary(state_descriptor, content)
        state_directory.rename(detached)
        return temporary

    monkeypatch.setattr(
        direction_module._DirectionLedgerStore,
        "_write_temporary",
        staticmethod(write_then_detach),
    )

    with pytest.raises(second_mate.DirectionConflictError, match="state directory"):
        second_mate.promote_direction(
            repository,
            candidate.to_json(),
            _approval(candidate),
            _promotion_grant(candidate),
        )

    assert not (repository / ".second-mate" / "directions.json").exists()
    assert not (detached / "directions.json").exists()
    assert list(detached.iterdir()) == []


def test_direction_promotion_refuses_detached_repository_root_before_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pinning state only to an open root fd must allow the whole target to move out."""
    repository = _make_repository(tmp_path)
    state_directory = repository / ".second-mate"
    state_directory.mkdir()
    candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    detached = tmp_path / "detached-target"
    original_write_temporary = direction_module._DirectionLedgerStore._write_temporary

    def write_then_detach_root(state_descriptor: int, content: bytes) -> str:
        temporary = original_write_temporary(state_descriptor, content)
        repository.rename(detached)
        repository.symlink_to(detached, target_is_directory=True)
        return temporary

    monkeypatch.setattr(
        direction_module._DirectionLedgerStore,
        "_write_temporary",
        staticmethod(write_then_detach_root),
    )

    with pytest.raises(second_mate.DirectionConflictError, match="repository root"):
        second_mate.promote_direction(
            repository,
            candidate.to_json(),
            _approval(candidate),
            _promotion_grant(candidate),
        )

    assert repository.is_symlink()
    assert not (detached / ".second-mate" / "directions.json").exists()
    assert list((detached / ".second-mate").iterdir()) == []


def test_direction_promotion_refuses_revision_drift_after_temporary_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Checking revision only before save must let drift precede ledger installation."""
    repository = _make_repository(tmp_path)
    state_directory = repository / ".second-mate"
    state_directory.mkdir()
    candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    original_write_temporary = direction_module._DirectionLedgerStore._write_temporary

    def write_then_drift(state_descriptor: int, content: bytes) -> str:
        temporary = original_write_temporary(state_descriptor, content)
        (repository / "README.md").write_text("Drift after temporary write.\n", encoding="utf-8")
        return temporary

    monkeypatch.setattr(
        direction_module._DirectionLedgerStore,
        "_write_temporary",
        staticmethod(write_then_drift),
    )

    with pytest.raises(second_mate.DirectionConflictError, match="revision drift"):
        second_mate.promote_direction(
            repository,
            candidate.to_json(),
            _approval(candidate),
            _promotion_grant(candidate),
        )

    assert not (state_directory / "directions.json").exists()
    assert not list(state_directory.glob(".directions.json.*.next"))


def test_direction_promotion_rolls_back_if_revision_drifts_during_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Omitting post-install validation must certify a ledger after outside drift."""
    repository = _make_repository(tmp_path)
    state_directory = repository / ".second-mate"
    state_directory.mkdir()
    candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    original_link = direction_module.os.link

    def link_then_drift(*args: object, **kwargs: object) -> None:
        original_link(*args, **kwargs)
        (repository / "README.md").write_text("Drift during install.\n", encoding="utf-8")

    monkeypatch.setattr(direction_module.os, "link", link_then_drift)

    with pytest.raises(second_mate.DirectionConflictError, match="revision drift"):
        second_mate.promote_direction(
            repository,
            candidate.to_json(),
            _approval(candidate),
            _promotion_grant(candidate),
        )

    assert not (state_directory / "directions.json").exists()
    assert not list(state_directory.glob(".directions.json.*.next"))


def test_changed_direction_rollback_restores_exact_previous_ledger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rolling back only an initial install must let invalid D-02 replace D-01 history."""
    repository = _make_repository(tmp_path)
    first_candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    second_mate.promote_direction(
        repository,
        first_candidate.to_json(),
        _approval(first_candidate),
        _promotion_grant(first_candidate),
    )
    ledger_path = repository / ".second-mate" / "directions.json"
    ledger_path.chmod(0o755)
    first_bytes = ledger_path.read_bytes()
    first_mode = stat.S_IMODE(ledger_path.stat().st_mode)
    second_candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit and preserve rollback truth.\n",
        direction_id="D-02",
        change_note="Preserve rollback truth.",
    )
    original_attachment_check = (
        direction_module._DirectionLedgerStore._assert_state_directory_attached
    )
    drifted = False

    def check_then_drift(root_descriptor: int, state_descriptor: int) -> None:
        nonlocal drifted
        original_attachment_check(root_descriptor, state_descriptor)
        if not drifted and ledger_path.exists():
            current = json.loads(ledger_path.read_bytes())
            if current["current_direction_id"] == "D-02":
                drifted = True
                (repository / "README.md").write_text(
                    "Drift during changed-Direction install.\n",
                    encoding="utf-8",
                )

    monkeypatch.setattr(
        direction_module._DirectionLedgerStore,
        "_assert_state_directory_attached",
        staticmethod(check_then_drift),
    )

    with pytest.raises(second_mate.DirectionConflictError, match="revision drift"):
        second_mate.promote_direction(
            repository,
            second_candidate.to_json(),
            _approval(second_candidate, approval_id="DA-02"),
            _promotion_grant(second_candidate, grant_id="DPG-02"),
        )

    assert drifted is True
    assert ledger_path.read_bytes() == first_bytes
    assert stat.S_IMODE(ledger_path.stat().st_mode) == first_mode
    assert second_mate.load_direction(repository).id == "D-01"


def test_changed_direction_does_not_erase_concurrent_history_before_exchange(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unconditional replace must erase competing history after the pre-install snapshot."""
    repository = _make_repository(tmp_path)
    first_candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    second_mate.promote_direction(
        repository,
        first_candidate.to_json(),
        _approval(first_candidate),
        _promotion_grant(first_candidate),
    )
    ledger_path = repository / ".second-mate" / "directions.json"
    first_bytes = ledger_path.read_bytes()
    intended = second_mate.prepare_direction(
        repository,
        "Keep intended D-02 meaning explicit.\n",
        direction_id="D-02",
        change_note="Add intended D-02 meaning.",
    )
    competing = second_mate.prepare_direction(
        repository,
        "Keep competing Direction meaning explicit.\n",
        direction_id="D-COMPETING",
        change_note="Add competing Direction meaning.",
    )
    second_mate.promote_direction(
        repository,
        competing.to_json(),
        _approval(competing, approval_id="DA-COMPETING"),
        _promotion_grant(competing, grant_id="DPG-COMPETING"),
    )
    competing_bytes = ledger_path.read_bytes()
    ledger_path.write_bytes(first_bytes)
    assert inspect_revision(repository).fingerprint == intended.promotion_basis.target_fingerprint

    original_attachment_check = (
        direction_module._DirectionLedgerStore._assert_state_directory_attached
    )
    attachment_checks_with_temporary = 0

    def check_then_compete(root_descriptor: int, state_descriptor: int) -> None:
        nonlocal attachment_checks_with_temporary
        original_attachment_check(root_descriptor, state_descriptor)
        if list((repository / ".second-mate").glob(".directions.json.*.next")):
            attachment_checks_with_temporary += 1
            if attachment_checks_with_temporary == 2:
                ledger_path.write_bytes(competing_bytes)

    monkeypatch.setattr(
        direction_module._DirectionLedgerStore,
        "_assert_state_directory_attached",
        staticmethod(check_then_compete),
    )

    with pytest.raises(second_mate.DirectionConflictError, match="history drift"):
        second_mate.promote_direction(
            repository,
            intended.to_json(),
            _approval(intended, approval_id="DA-02"),
            _promotion_grant(intended, grant_id="DPG-02"),
        )

    assert attachment_checks_with_temporary >= 2
    assert ledger_path.read_bytes() == competing_bytes
    assert second_mate.load_direction(repository).id == "D-COMPETING"


def test_changed_direction_restores_concurrent_symlink_history_during_exchange(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Discarding a displaced non-file must erase the concurrent history entry."""
    repository = _make_repository(tmp_path)
    first_candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    second_mate.promote_direction(
        repository,
        first_candidate.to_json(),
        _approval(first_candidate),
        _promotion_grant(first_candidate),
    )
    intended = second_mate.prepare_direction(
        repository,
        "Keep intended D-02 meaning explicit.\n",
        direction_id="D-02",
        change_note="Add intended D-02 meaning.",
    )
    ledger_path = repository / ".second-mate" / "directions.json"
    victim = tmp_path / "outside-history.json"
    victim.write_text("outside history must remain exact\n", encoding="utf-8")
    original_attachment_check = (
        direction_module._DirectionLedgerStore._assert_state_directory_attached
    )
    attachment_checks_with_temporary = 0

    def check_then_replace_with_symlink(root_descriptor: int, state_descriptor: int) -> None:
        nonlocal attachment_checks_with_temporary
        original_attachment_check(root_descriptor, state_descriptor)
        if list((repository / ".second-mate").glob(".directions.json.*.next")):
            attachment_checks_with_temporary += 1
            if attachment_checks_with_temporary == 2:
                ledger_path.unlink()
                ledger_path.symlink_to(victim)

    monkeypatch.setattr(
        direction_module._DirectionLedgerStore,
        "_assert_state_directory_attached",
        staticmethod(check_then_replace_with_symlink),
    )

    with pytest.raises(second_mate.DirectionConflictError, match="history drift"):
        second_mate.promote_direction(
            repository,
            intended.to_json(),
            _approval(intended, approval_id="DA-02"),
            _promotion_grant(intended, grant_id="DPG-02"),
        )

    assert attachment_checks_with_temporary >= 2
    assert ledger_path.is_symlink()
    assert victim.read_text(encoding="utf-8") == "outside history must remain exact\n"


def test_direction_temporary_is_removed_when_file_fsync_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Leaving a failed randomized temp must poison retry with unrelated revision drift."""
    repository = _make_repository(tmp_path)
    state_directory = repository / ".second-mate"
    state_directory.mkdir()
    candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    original_fsync = direction_module.os.fsync
    failed = False

    def fail_temporary_fsync(descriptor: int) -> None:
        nonlocal failed
        metadata = direction_module.os.fstat(descriptor)
        if not failed and stat.S_ISREG(metadata.st_mode):
            failed = True
            raise OSError("fixture temporary fsync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(direction_module.os, "fsync", fail_temporary_fsync)

    with pytest.raises(second_mate.DirectionConflictError, match="temporary"):
        second_mate.promote_direction(
            repository,
            candidate.to_json(),
            _approval(candidate),
            _promotion_grant(candidate),
        )

    assert failed is True
    assert not (state_directory / "directions.json").exists()
    assert not list(state_directory.glob(".directions.json.*.next"))


def test_direction_prepare_refuses_project_authority_ignored_by_git(tmp_path: Path) -> None:
    """Allowing an ignored ledger must hide accepted Direction from preflight and handoff."""
    repository = _make_repository(tmp_path)
    (repository / ".gitignore").write_text(".second-mate/\n", encoding="utf-8")
    _run_git(repository, "add", ".gitignore")
    _run_git(repository, "commit", "-q", "-m", "ignore coordinator state")

    with pytest.raises(second_mate.ValidationError, match="must not be ignored"):
        second_mate.prepare_direction(
            repository,
            "Keep authority explicit.\n",
            direction_id="D-01",
            change_note=None,
        )

    assert not (repository / ".second-mate").exists()


def test_new_direction_after_preflight_invalidates_stale_execution_consent(tmp_path: Path) -> None:
    """Hiding the ledger from revision facts must let an old Direction packet dispatch."""
    repository = make_fs01_repository(tmp_path)
    first_candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    first = second_mate.promote_direction(
        repository,
        first_candidate.to_json(),
        _approval(first_candidate),
        _promotion_grant(first_candidate),
    )
    draft = second_mate.create_draft(first.direction.to_json(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    execution_grant = exact_grant(draft, basis)
    second_candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit and retain rejected boundaries.\n",
        direction_id="D-02",
        change_note="Retain rejected boundaries.",
    )
    second_mate.promote_direction(
        repository,
        second_candidate.to_json(),
        _approval(second_candidate, approval_id="DA-02"),
        _promotion_grant(second_candidate, grant_id="DPG-02"),
    )
    executor = RecordingExecutor()

    with pytest.raises(second_mate.AuthorityError, match="revision drift"):
        second_mate.start_run(
            draft=draft,
            basis=basis,
            grant_data=execution_grant,
            repository=repository,
            executor=executor,
            owner_id="stale-direction-owner",
        )

    assert executor.requests == []
    assert not (repository / ".second-mate" / "state.json").exists()


def test_approved_direction_remains_in_preflight_after_late_ignore_rule(tmp_path: Path) -> None:
    """Excluding an accepted ledger later must not hide forged authority from preflight."""
    repository = make_fs01_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    promoted = second_mate.promote_direction(
        repository,
        candidate.to_json(),
        _approval(candidate),
        _promotion_grant(candidate),
    )
    (repository / ".gitignore").write_text(".second-mate/\n", encoding="utf-8")
    _run_git(repository, "add", ".gitignore")
    _run_git(repository, "commit", "-q", "-m", "late ignore rule")
    draft = second_mate.create_draft(promoted.direction.to_json(), valid_packet())
    before = second_mate.preflight(draft, repository)

    ledger_path = repository / ".second-mate" / "directions.json"
    ledger = json.loads(ledger_path.read_bytes())
    version = ledger["versions"][0]
    version["approval"]["approved_by"] = "forged-human"
    version["direction"]["approval"]["approved_by"] = "forged-human"
    version["direction_digest"] = digest_json(version["direction"])
    ledger_path.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    assert second_mate.load_direction(repository).approval.approved_by == "forged-human"
    after = second_mate.preflight(draft, repository)

    assert any(fact.path == ".second-mate/directions.json" for fact in before.record.revision.files)
    assert after.record.revision.fingerprint != before.record.revision.fingerprint
    assert after.digest != before.digest
