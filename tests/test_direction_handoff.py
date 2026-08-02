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
from test_draft import valid_direction, valid_packet
from test_preflight import make_repository as make_fs01_repository

import second_mate
import second_mate.direction as direction_module
from second_mate.domain import digest_json
from second_mate.repository import inspect_revision
from second_mate.service import ExecutionResult
from second_mate.store import FileStateStore, PosixAtomicWriter


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


@pytest.mark.parametrize(
    ("document_name", "invalid_version"),
    (
        ("candidate_envelope", True),
        ("candidate", 1.0),
        ("approval", True),
        ("grant", 1.0),
    ),
)
def test_direction_authority_requires_integer_schema_version_one(
    tmp_path: Path,
    document_name: str,
    invalid_version: object,
) -> None:
    repository = _make_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Keep human meaning explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    candidate_data = copy.deepcopy(candidate.to_json())
    approval_data = _approval(candidate)
    grant_data = _promotion_grant(candidate)
    if document_name == "candidate_envelope":
        candidate_data["schema_version"] = invalid_version
    elif document_name == "candidate":
        candidate_data["candidate"]["schema_version"] = invalid_version
    elif document_name == "approval":
        approval_data["schema_version"] = invalid_version
    else:
        grant_data["schema_version"] = invalid_version

    with pytest.raises(second_mate.ValidationError, match="integer 1"):
        second_mate.promote_direction(
            repository,
            candidate_data,
            approval_data,
            grant_data,
        )

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

    stale_data = stale_candidate.to_json()
    stale_basis = stale_data["promotion_basis"]
    assert isinstance(stale_basis, dict)
    current_revision = inspect_revision(repository)
    stale_basis["target_head"] = current_revision.head
    stale_basis["target_fingerprint"] = current_revision.fingerprint
    stale_grant = _promotion_grant(stale_candidate, grant_id="DPG-STALE")
    stale_grant["target_head"] = current_revision.head
    stale_grant["target_fingerprint"] = current_revision.fingerprint
    with pytest.raises(second_mate.DirectionConflictError, match="stale Direction candidate"):
        second_mate.promote_direction(
            repository,
            stale_data,
            _approval(stale_candidate, approval_id="DA-STALE"),
            stale_grant,
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


@pytest.mark.parametrize("recorded_in", ("head", "index"))
def test_missing_git_recorded_direction_history_cannot_restart_the_chain(
    tmp_path: Path,
    recorded_in: str,
) -> None:
    """A missing tracked ledger must not be mistaken for never-created history."""
    repository = _make_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Keep immutable history explicit.\n",
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
    _run_git(repository, "add", ledger_path.relative_to(repository).as_posix())
    if recorded_in == "head":
        _run_git(repository, "commit", "-q", "-m", "record approved Direction")
    ledger_path.unlink()

    with pytest.raises(second_mate.DirectionConflictError, match=r"history.*missing"):
        second_mate.prepare_direction(
            repository,
            "Attempt to restart a lost chain.\n",
            direction_id="D-NEW",
            change_note=None,
        )

    assert not ledger_path.exists()


@pytest.mark.parametrize("retained_history_field", ("supersedes", "change_note"))
def test_candidate_requiring_missing_untracked_history_cannot_become_initial(
    tmp_path: Path,
    retained_history_field: str,
) -> None:
    repository = _make_repository(tmp_path)
    first_candidate = second_mate.prepare_direction(
        repository,
        "Keep the initial chain explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    second_mate.promote_direction(
        repository,
        first_candidate.to_json(),
        _approval(first_candidate),
        _promotion_grant(first_candidate),
    )
    second_candidate = second_mate.prepare_direction(
        repository,
        "Keep missing-history rejection explicit.\n",
        direction_id="D-02",
        change_note="Exercise missing-history shape validation.",
    )
    ledger_path = repository / ".second-mate" / "directions.json"
    ledger_path.unlink()
    candidate_data = second_candidate.to_json()
    candidate_body = candidate_data["candidate"]
    assert isinstance(candidate_body, dict)
    if retained_history_field == "supersedes":
        candidate_body["change_note"] = None
    else:
        candidate_body["supersedes"] = None
    candidate_digest = digest_json(candidate_body)
    candidate_data["candidate_digest"] = candidate_digest
    revision = inspect_revision(repository)
    promotion_basis = candidate_data["promotion_basis"]
    assert isinstance(promotion_basis, dict)
    promotion_basis["target_head"] = revision.head
    promotion_basis["target_fingerprint"] = revision.fingerprint
    approval = _approval(second_candidate, approval_id="DA-02")
    approval["candidate_digest"] = candidate_digest
    grant = _promotion_grant(second_candidate, grant_id="DPG-02")
    grant["candidate_digest"] = candidate_digest
    grant["target_head"] = revision.head
    grant["target_fingerprint"] = revision.fingerprint

    with pytest.raises(second_mate.DirectionConflictError, match="history that does not exist"):
        second_mate.promote_direction(repository, candidate_data, approval, grant)

    assert not ledger_path.exists()


def test_direction_and_approval_ids_cannot_be_reused(tmp_path: Path) -> None:
    repository = _make_repository(tmp_path)
    first_candidate = second_mate.prepare_direction(
        repository,
        "Keep immutable identity explicit.\n",
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

    with pytest.raises(second_mate.DirectionConflictError, match=r"Direction id.*reused"):
        second_mate.prepare_direction(
            repository,
            "Attempt to reuse immutable Direction identity.\n",
            direction_id="D-01",
            change_note="Try to reuse the old identity.",
        )

    second_candidate = second_mate.prepare_direction(
        repository,
        "Keep immutable approval identity explicit.\n",
        direction_id="D-02",
        change_note="Exercise approval identity uniqueness.",
    )
    with pytest.raises(second_mate.DirectionConflictError, match=r"approval id.*reused"):
        second_mate.promote_direction(
            repository,
            second_candidate.to_json(),
            _approval(second_candidate, approval_id="DA-01"),
            _promotion_grant(second_candidate, grant_id="DPG-02"),
        )

    assert ledger_path.read_bytes() == first_bytes
    assert second_mate.load_direction(repository).id == "D-01"


def test_unchanged_direction_text_cannot_create_a_new_version(tmp_path: Path) -> None:
    repository = _make_repository(tmp_path)
    first_text = "Keep approved meaning exact.\n"
    first_candidate = second_mate.prepare_direction(
        repository,
        first_text,
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

    with pytest.raises(second_mate.ValidationError, match="must change the exact approved text"):
        second_mate.prepare_direction(
            repository,
            first_text,
            direction_id="D-02",
            change_note="Attempt an unchanged replacement.",
        )

    changed_candidate = second_mate.prepare_direction(
        repository,
        "Prepare a candidate that will be tampered back to old meaning.\n",
        direction_id="D-02",
        change_note="Exercise promotion's unchanged-text guard.",
    )
    candidate_data = changed_candidate.to_json()
    candidate_body = candidate_data["candidate"]
    assert isinstance(candidate_body, dict)
    candidate_body["text"] = first_text
    candidate_digest = digest_json(candidate_body)
    candidate_data["candidate_digest"] = candidate_digest
    approval = _approval(changed_candidate, approval_id="DA-02")
    approval["candidate_digest"] = candidate_digest
    grant = _promotion_grant(changed_candidate, grant_id="DPG-02")
    grant["candidate_digest"] = candidate_digest

    with pytest.raises(second_mate.ValidationError, match="must change the exact approved text"):
        second_mate.promote_direction(repository, candidate_data, approval, grant)

    assert ledger_path.read_bytes() == first_bytes
    assert second_mate.load_direction(repository).id == "D-01"


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


def test_direction_ledger_rejects_duplicate_fields_at_any_nesting_level(tmp_path: Path) -> None:
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
    ledger_text = ledger_path.read_text(encoding="utf-8")
    approved_at = '          "approved_at": "2026-08-02T12:00:00Z"'
    assert ledger_text.count(approved_at) == 1
    ledger_path.write_text(
        ledger_text.replace(
            approved_at,
            '          "approved_at": "contradictory",\n' + approved_at,
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(second_mate.ValidationError, match="duplicate"):
        second_mate.load_direction(repository)


@pytest.mark.parametrize("invalid_version", (True, 1.0))
def test_direction_ledger_requires_literal_nested_direction_schema_version(
    tmp_path: Path,
    invalid_version: object,
) -> None:
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
    ledger["versions"][0]["direction"]["schema_version"] = invalid_version
    ledger_path.write_text(
        json.dumps(ledger, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(second_mate.ValidationError, match="integer 1"):
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
    ("document", "field", "invalid_value"),
    (
        ("approval", "direction_id", "D-DIFFERENT"),
        ("grant", "candidate_digest", "0" * 64),
        ("grant", "target_root", "/different/target"),
        ("grant", "target_head", "different-head"),
        ("grant", "target_fingerprint", "f" * 64),
    ),
)
def test_approval_and_grant_must_bind_the_exact_candidate_and_target(
    tmp_path: Path,
    document: str,
    field: str,
    invalid_value: str,
) -> None:
    repository = _make_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Keep exact authority binding explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    approval = _approval(candidate)
    grant = _promotion_grant(candidate)
    if document == "approval":
        approval[field] = invalid_value
        expected_error = "approval identifies a different candidate"
    else:
        grant[field] = invalid_value
        expected_error = f"promotion grant {field}"

    with pytest.raises(second_mate.ValidationError, match=expected_error):
        second_mate.promote_direction(
            repository,
            candidate.to_json(),
            approval,
            grant,
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


class _FailFinalStateWrite:
    def __init__(self) -> None:
        self.delegate = PosixAtomicWriter()

    def write(self, path: Path, content: bytes) -> None:
        if path.name == "state.json":
            raise OSError("targeted failure after close journal")
        self.delegate.write(path, content)


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


def test_direction_promotion_refuses_pending_run_close_recovery(tmp_path: Path) -> None:
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
        owner_id="pending-close-owner",
    )
    second_mate.record_evidence(repository)
    second_candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit after a recovered close.\n",
        direction_id="D-02",
        change_note="Wait for clean-close recovery.",
    )
    state_path = repository / ".second-mate" / "state.json"
    with pytest.raises(second_mate.CloseFailure):
        second_mate.clean_close(
            repository,
            direction_coverage="still_remaining",
            residual_uncertainty=("Direction promotion remains separately authorized.",),
            handoff="Recover the run close before changing Direction.",
            store=FileStateStore(state_path, writer=_FailFinalStateWrite()),
        )
    pending_path = state_path.with_name("state.json.pending")
    state_bytes = state_path.read_bytes()
    pending_bytes = pending_path.read_bytes()

    with pytest.raises(second_mate.DirectionConflictError, match="pending run-state close"):
        second_mate.promote_direction(
            repository,
            second_candidate.to_json(),
            _approval(second_candidate, approval_id="DA-02"),
            _promotion_grant(second_candidate, grant_id="DPG-02"),
        )

    assert state_path.read_bytes() == state_bytes
    assert pending_path.read_bytes() == pending_bytes
    assert second_mate.load_direction(repository).id == "D-01"


def test_direction_promotion_rejects_malformed_closed_run_state(
    tmp_path: Path,
) -> None:
    repository = _make_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    state_directory = repository / ".second-mate"
    state_directory.mkdir()
    state_path = state_directory / "state.json"
    state_path.write_text(
        '{"closed":true,"unexpected":"target drift"}\n',
        encoding="utf-8",
    )
    state_bytes = state_path.read_bytes()

    with pytest.raises(second_mate.ValidationError, match="state fields"):
        second_mate.promote_direction(
            repository,
            candidate.to_json(),
            _approval(candidate),
            _promotion_grant(candidate),
        )

    assert state_path.read_bytes() == state_bytes
    assert not (state_directory / "directions.json").exists()


def test_closed_run_state_created_after_prepare_invalidates_promotion_basis(
    tmp_path: Path,
) -> None:
    source_parent = tmp_path / "closed-state-source"
    source_parent.mkdir()
    source = make_fs01_repository(source_parent)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, source)
    second_mate.start_run(
        draft=draft,
        basis=basis,
        grant_data=exact_grant(draft, basis),
        repository=source,
        executor=second_mate.FixtureExecutor(),
        owner_id="closed-state-source-owner",
    )
    second_mate.record_evidence(source)
    second_mate.clean_close(
        source,
        direction_coverage="still_remaining",
        residual_uncertainty=("Direction handoff remains independently authorized.",),
        handoff="The fixture run is closed before Direction promotion.",
    )
    source_state = json.loads((source / ".second-mate" / "state.json").read_bytes())

    repository = _make_repository(tmp_path)
    candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    state_directory = repository / ".second-mate"
    state_directory.mkdir()
    state_path = state_directory / "state.json"
    state_path.write_text(
        json.dumps(source_state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    state_bytes = state_path.read_bytes()

    with pytest.raises(second_mate.DirectionConflictError, match="revision drift"):
        second_mate.promote_direction(
            repository,
            candidate.to_json(),
            _approval(candidate),
            _promotion_grant(candidate),
        )

    assert state_path.read_bytes() == state_bytes
    assert not (state_directory / "directions.json").exists()


@pytest.mark.parametrize("false_close_marker", ("closed", "phase", "route"))
def test_direction_rejects_open_run_state_falsely_marked_closed(
    tmp_path: Path,
    false_close_marker: str,
) -> None:
    source_parent = tmp_path / "false-closed-state-source"
    source_parent.mkdir()
    source = make_fs01_repository(source_parent)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, source)
    second_mate.start_run(
        draft=draft,
        basis=basis,
        grant_data=exact_grant(draft, basis),
        repository=source,
        executor=second_mate.FixtureExecutor(),
        owner_id="false-closed-state-source-owner",
    )
    false_closed_state = json.loads((source / ".second-mate" / "state.json").read_bytes())
    if false_close_marker == "closed":
        false_closed_state["closed"] = True
    elif false_close_marker == "phase":
        false_closed_state["run"]["phase"] = "closed"
    else:
        false_closed_state["route_status"] = "completed"

    repository = _make_repository(tmp_path)
    state_directory = repository / ".second-mate"
    state_directory.mkdir()
    state_path = state_directory / "state.json"
    state_path.write_text(
        json.dumps(false_closed_state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    state_bytes = state_path.read_bytes()

    with pytest.raises(second_mate.ValidationError, match="closed status is inconsistent"):
        second_mate.prepare_direction(
            repository,
            "Keep authority explicit.\n",
            direction_id="D-01",
            change_note=None,
        )

    assert state_path.read_bytes() == state_bytes
    assert not (state_directory / "directions.json").exists()


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

    def write_then_detach(
        state_descriptor: int,
        content: bytes,
    ) -> direction_module._OwnedTemporary:
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

    def write_then_detach_root(
        state_descriptor: int,
        content: bytes,
    ) -> direction_module._OwnedTemporary:
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

    def write_then_drift(
        state_descriptor: int,
        content: bytes,
    ) -> direction_module._OwnedTemporary:
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


@pytest.mark.parametrize("replacement_kind", ("file", "symlink"))
def test_initial_direction_pins_owned_temporary_across_link(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement_kind: str,
) -> None:
    """A replaced temp must not become initial project authority through hard-linking."""
    repository = _make_repository(tmp_path)
    state_directory = repository / ".second-mate"
    state_directory.mkdir()
    candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    marker_content = b"unowned initial replacement must be retained\n"
    victim = tmp_path / "outside-initial-temp-target.json"
    victim.write_text("outside initial target remains exact\n", encoding="utf-8")
    original_link = direction_module.os.link
    replaced = False

    def replace_temporary_then_link(*args: object, **kwargs: object) -> None:
        nonlocal replaced
        source = args[0]
        assert isinstance(source, str)
        temporary_path = state_directory / source
        temporary_path.unlink()
        if replacement_kind == "file":
            temporary_path.write_bytes(marker_content)
            temporary_path.chmod(0o600)
        else:
            temporary_path.symlink_to(victim)
        replaced = True
        original_link(*args, **kwargs)

    monkeypatch.setattr(direction_module.os, "link", replace_temporary_then_link)

    with pytest.raises(second_mate.DirectionConflictError):
        second_mate.promote_direction(
            repository,
            candidate.to_json(),
            _approval(candidate),
            _promotion_grant(candidate),
        )

    assert replaced is True
    assert not (state_directory / "directions.json").exists()
    recovery_entries = list(state_directory.glob(".directions.json.*.next"))
    assert len(recovery_entries) == 1
    if replacement_kind == "file":
        assert recovery_entries[0].read_bytes() == marker_content
        assert stat.S_IMODE(recovery_entries[0].stat().st_mode) == 0o600
    else:
        assert recovery_entries[0].is_symlink()
        assert recovery_entries[0].readlink() == victim
        assert victim.read_text(encoding="utf-8") == "outside initial target remains exact\n"


@pytest.mark.parametrize("concurrent_kind", ("file", "symlink"))
def test_initial_direction_rollback_preserves_a_concurrent_final_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    concurrent_kind: str,
) -> None:
    """Check-then-unlink must not delete a final entry installed during rollback."""
    repository = _make_repository(tmp_path)
    state_directory = repository / ".second-mate"
    state_directory.mkdir()
    candidate = second_mate.prepare_direction(
        repository,
        "Keep authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    ledger_path = state_directory / "directions.json"
    victim = tmp_path / "outside-concurrent-history.json"
    victim.write_text("outside concurrent history remains exact\n", encoding="utf-8")
    concurrent_content = b"concurrent project history remains exact\n"
    original_link = direction_module.os.link

    def link_then_drift(*args: object, **kwargs: object) -> None:
        original_link(*args, **kwargs)
        (repository / "README.md").write_text(
            "Drift during initial Direction install.\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(direction_module.os, "link", link_then_drift)
    original_move = direction_module._DirectionLedgerStore._move_path_no_replace
    injected = False

    def replace_final_then_move(
        state_descriptor: int,
        source: str,
        destination: str,
    ) -> None:
        nonlocal injected
        if not injected and source == "directions.json":
            injected = True
            ledger_path.unlink()
            if concurrent_kind == "file":
                ledger_path.write_bytes(concurrent_content)
                ledger_path.chmod(0o600)
            else:
                ledger_path.symlink_to(victim)
        original_move(state_descriptor, source, destination)

    monkeypatch.setattr(
        direction_module._DirectionLedgerStore,
        "_move_path_no_replace",
        staticmethod(replace_final_then_move),
    )

    with pytest.raises(second_mate.DirectionConflictError):
        second_mate.promote_direction(
            repository,
            candidate.to_json(),
            _approval(candidate),
            _promotion_grant(candidate),
        )

    assert injected is True
    if concurrent_kind == "file":
        assert ledger_path.read_bytes() == concurrent_content
        assert stat.S_IMODE(ledger_path.stat().st_mode) == 0o600
    else:
        assert ledger_path.is_symlink()
        assert ledger_path.readlink() == victim
        assert victim.read_text(encoding="utf-8") == ("outside concurrent history remains exact\n")


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


@pytest.mark.parametrize("replacement_kind", ("file", "symlink"))
def test_changed_direction_retains_replaced_displaced_history_during_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement_kind: str,
) -> None:
    """Cleanup must not erase an entry replacing the displaced prior-history temp."""
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
    state_directory = repository / ".second-mate"
    ledger_path = state_directory / "directions.json"
    ledger_path.chmod(0o755)
    first_bytes = ledger_path.read_bytes()
    first_mode = stat.S_IMODE(ledger_path.stat().st_mode)
    intended = second_mate.prepare_direction(
        repository,
        "Keep authority explicit through cleanup.\n",
        direction_id="D-02",
        change_note="Exercise displaced-history cleanup.",
    )
    marker_content = b"unowned cleanup replacement must be retained\n"
    victim = tmp_path / "outside-cleanup-target.json"
    victim.write_text("outside cleanup target remains exact\n", encoding="utf-8")
    original_discard = direction_module._DirectionLedgerStore._discard_if_exact
    injected = False

    def replace_displaced_then_discard(
        state_descriptor: int,
        name: str,
        expected: direction_module._PathEntry,
    ) -> None:
        nonlocal injected
        if not injected and expected.content == first_bytes:
            injected = True
            temporary_path = state_directory / name
            temporary_path.unlink()
            if replacement_kind == "file":
                temporary_path.write_bytes(marker_content)
                temporary_path.chmod(0o600)
            else:
                temporary_path.symlink_to(victim)
        original_discard(state_descriptor, name, expected)

    monkeypatch.setattr(
        direction_module._DirectionLedgerStore,
        "_discard_if_exact",
        staticmethod(replace_displaced_then_discard),
    )

    with pytest.raises(second_mate.DirectionConflictError, match="retained"):
        second_mate.promote_direction(
            repository,
            intended.to_json(),
            _approval(intended, approval_id="DA-02"),
            _promotion_grant(intended, grant_id="DPG-02"),
        )

    assert injected is True
    assert ledger_path.read_bytes() == first_bytes
    assert stat.S_IMODE(ledger_path.stat().st_mode) == first_mode
    assert second_mate.load_direction(repository).id == "D-01"
    recovery_entries = list(state_directory.glob(".directions.json.*.next"))
    assert len(recovery_entries) == 1
    if replacement_kind == "file":
        assert recovery_entries[0].read_bytes() == marker_content
        assert stat.S_IMODE(recovery_entries[0].stat().st_mode) == 0o600
    else:
        assert recovery_entries[0].is_symlink()
        assert recovery_entries[0].readlink() == victim
        assert victim.read_text(encoding="utf-8") == "outside cleanup target remains exact\n"


def test_changed_direction_rolls_back_revision_drift_after_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The finalization guard must reject drift introduced after normal temp cleanup."""
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
    state_directory = repository / ".second-mate"
    ledger_path = state_directory / "directions.json"
    ledger_path.chmod(0o755)
    first_bytes = ledger_path.read_bytes()
    first_mode = stat.S_IMODE(ledger_path.stat().st_mode)
    intended = second_mate.prepare_direction(
        repository,
        "Keep authority explicit through finalization.\n",
        direction_id="D-02",
        change_note="Exercise post-cleanup finalization.",
    )
    original_discard = direction_module._DirectionLedgerStore._discard_if_exact
    drifted = False

    def discard_then_drift(
        state_descriptor: int,
        name: str,
        expected: direction_module._PathEntry,
    ) -> None:
        nonlocal drifted
        original_discard(state_descriptor, name, expected)
        if not drifted and expected.content == first_bytes:
            drifted = True
            (repository / "README.md").write_text(
                "Drift after displaced-history cleanup.\n",
                encoding="utf-8",
            )

    monkeypatch.setattr(
        direction_module._DirectionLedgerStore,
        "_discard_if_exact",
        staticmethod(discard_then_drift),
    )

    with pytest.raises(second_mate.DirectionConflictError, match="finalization"):
        second_mate.promote_direction(
            repository,
            intended.to_json(),
            _approval(intended, approval_id="DA-02"),
            _promotion_grant(intended, grant_id="DPG-02"),
        )

    assert drifted is True
    assert ledger_path.read_bytes() == first_bytes
    assert stat.S_IMODE(ledger_path.stat().st_mode) == first_mode
    assert second_mate.load_direction(repository).id == "D-01"
    assert not list(state_directory.glob(".directions.json.*.next"))


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


def test_changed_direction_fails_closed_without_atomic_exchange(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    monkeypatch.setattr(direction_module.ctypes, "CDLL", lambda *args, **kwargs: object())

    with pytest.raises(second_mate.ValidationError, match=r"atomic.*unavailable"):
        second_mate.promote_direction(
            repository,
            intended.to_json(),
            _approval(intended, approval_id="DA-02"),
            _promotion_grant(intended, grant_id="DPG-02"),
        )

    assert ledger_path.read_bytes() == first_bytes
    assert second_mate.load_direction(repository).id == "D-01"
    assert not list(ledger_path.parent.glob(".directions.json.*.next"))


@pytest.mark.parametrize("replacement_kind", ("file", "symlink"))
def test_changed_direction_pins_owned_temporary_across_exchange(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement_kind: str,
) -> None:
    """Replacing the owned temp must not install it or delete prior history."""
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
    state_directory = repository / ".second-mate"
    ledger_path = state_directory / "directions.json"
    first_bytes = ledger_path.read_bytes()
    marker_content = b"unowned replacement must be retained\n"
    victim = tmp_path / "outside-temp-target.json"
    victim.write_text("outside temp target remains exact\n", encoding="utf-8")
    original_exchange = direction_module._DirectionLedgerStore._exchange_paths
    exchange_count = 0

    def replace_temporary_then_exchange(
        state_descriptor: int,
        left: str,
        right: str,
    ) -> None:
        nonlocal exchange_count
        exchange_count += 1
        if exchange_count == 1:
            temporary_path = state_directory / left
            temporary_path.unlink()
            if replacement_kind == "file":
                temporary_path.write_bytes(marker_content)
                temporary_path.chmod(0o600)
            else:
                temporary_path.symlink_to(victim)
        original_exchange(state_descriptor, left, right)

    monkeypatch.setattr(
        direction_module._DirectionLedgerStore,
        "_exchange_paths",
        staticmethod(replace_temporary_then_exchange),
    )

    with pytest.raises(second_mate.DirectionConflictError):
        second_mate.promote_direction(
            repository,
            intended.to_json(),
            _approval(intended, approval_id="DA-02"),
            _promotion_grant(intended, grant_id="DPG-02"),
        )

    assert exchange_count >= 2
    assert ledger_path.read_bytes() == first_bytes
    assert second_mate.load_direction(repository).id == "D-01"
    recovery_entries = list(state_directory.glob(".directions.json.*.next"))
    assert len(recovery_entries) == 1
    if replacement_kind == "file":
        assert recovery_entries[0].read_bytes() == marker_content
        assert stat.S_IMODE(recovery_entries[0].stat().st_mode) == 0o600
    else:
        assert recovery_entries[0].is_symlink()
        assert recovery_entries[0].readlink() == victim
        assert victim.read_text(encoding="utf-8") == "outside temp target remains exact\n"


@pytest.mark.parametrize("late_kind", ("file", "symlink"))
def test_changed_direction_retains_late_entry_displaced_by_recovery_exchange(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    late_kind: str,
) -> None:
    """Recovery must validate and retain what its second exchange displaces."""
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
    state_directory = ledger_path.parent
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
    late = second_mate.prepare_direction(
        repository,
        "Keep late Direction meaning explicit.\n",
        direction_id="D-LATE",
        change_note="Add late Direction meaning.",
    )
    second_mate.promote_direction(
        repository,
        competing.to_json(),
        _approval(competing, approval_id="DA-COMPETING"),
        _promotion_grant(competing, grant_id="DPG-COMPETING"),
    )
    competing_bytes = ledger_path.read_bytes()
    ledger_path.write_bytes(first_bytes)
    second_mate.promote_direction(
        repository,
        late.to_json(),
        _approval(late, approval_id="DA-LATE"),
        _promotion_grant(late, grant_id="DPG-LATE"),
    )
    late_bytes = ledger_path.read_bytes()
    ledger_path.write_bytes(first_bytes)
    victim = tmp_path / "outside-late-history.json"
    victim.write_text("outside late history remains exact\n", encoding="utf-8")
    original_exchange = direction_module._DirectionLedgerStore._exchange_paths
    exchange_count = 0

    def compete_during_each_exchange(
        state_descriptor: int,
        left: str,
        right: str,
    ) -> None:
        nonlocal exchange_count
        exchange_count += 1
        if exchange_count == 1:
            ledger_path.write_bytes(competing_bytes)
        elif exchange_count == 2:
            ledger_path.unlink()
            if late_kind == "file":
                ledger_path.write_bytes(late_bytes)
                ledger_path.chmod(0o600)
            else:
                ledger_path.symlink_to(victim)
        original_exchange(state_descriptor, left, right)

    monkeypatch.setattr(
        direction_module._DirectionLedgerStore,
        "_exchange_paths",
        staticmethod(compete_during_each_exchange),
    )

    with pytest.raises(second_mate.DirectionConflictError, match="retained"):
        second_mate.promote_direction(
            repository,
            intended.to_json(),
            _approval(intended, approval_id="DA-02"),
            _promotion_grant(intended, grant_id="DPG-02"),
        )

    assert exchange_count == 2
    assert ledger_path.read_bytes() == competing_bytes
    assert second_mate.load_direction(repository).id == "D-COMPETING"
    recovery_entries = list(state_directory.glob(".directions.json.*.next"))
    assert len(recovery_entries) == 1
    if late_kind == "file":
        assert recovery_entries[0].read_bytes() == late_bytes
        assert stat.S_IMODE(recovery_entries[0].stat().st_mode) == 0o600
    else:
        assert recovery_entries[0].is_symlink()
        assert recovery_entries[0].readlink() == victim
        assert victim.read_text(encoding="utf-8") == "outside late history remains exact\n"


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


@pytest.mark.parametrize("replacement_kind", ("file", "symlink"))
def test_failed_direction_temporary_write_retains_a_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement_kind: str,
) -> None:
    repository = _make_repository(tmp_path)
    state_directory = repository / ".second-mate"
    state_directory.mkdir()
    candidate = second_mate.prepare_direction(
        repository,
        "Keep failure cleanup authority explicit.\n",
        direction_id="D-01",
        change_note=None,
    )
    marker_content = b"unowned failed-write replacement must remain\n"
    victim = tmp_path / "outside-failed-write-target.json"
    victim.write_text("outside failed-write target remains exact\n", encoding="utf-8")
    original_fsync = direction_module.os.fsync
    injected = False

    def replace_temporary_then_fail(descriptor: int) -> None:
        nonlocal injected
        metadata = direction_module.os.fstat(descriptor)
        if not injected and stat.S_ISREG(metadata.st_mode):
            temporary_entries = list(state_directory.glob(".directions.json.*.next"))
            assert len(temporary_entries) == 1
            temporary_path = temporary_entries[0]
            temporary_path.unlink()
            if replacement_kind == "file":
                temporary_path.write_bytes(marker_content)
                temporary_path.chmod(0o600)
            else:
                temporary_path.symlink_to(victim)
            injected = True
            raise OSError("fixture failure after temporary replacement")
        original_fsync(descriptor)

    monkeypatch.setattr(direction_module.os, "fsync", replace_temporary_then_fail)

    with pytest.raises(second_mate.DirectionConflictError, match="temporary"):
        second_mate.promote_direction(
            repository,
            candidate.to_json(),
            _approval(candidate),
            _promotion_grant(candidate),
        )

    assert injected is True
    assert not (state_directory / "directions.json").exists()
    recovery_entries = list(state_directory.glob(".directions.json.*.next"))
    assert len(recovery_entries) == 1
    if replacement_kind == "file":
        assert recovery_entries[0].read_bytes() == marker_content
        assert stat.S_IMODE(recovery_entries[0].stat().st_mode) == 0o600
    else:
        assert recovery_entries[0].is_symlink()
        assert recovery_entries[0].readlink() == victim
        assert victim.read_text(encoding="utf-8") == "outside failed-write target remains exact\n"


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
