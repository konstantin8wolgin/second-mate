from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

import second_mate
from second_mate.domain import digest_json


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
        second_mate.promote_direction(repository, candidate.to_json(), approval)

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
        second_mate.promote_direction(repository, duplicate, _approval(candidate))
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

    with pytest.raises(second_mate.DirectionConflictError, match="stale"):
        second_mate.promote_direction(
            repository,
            stale_candidate.to_json(),
            _approval(stale_candidate, approval_id="DA-STALE"),
        )
    with pytest.raises(second_mate.ValidationError, match="change note"):
        second_mate.prepare_direction(
            repository,
            "A third version without an explanation.\n",
            direction_id="D-03",
            change_note=None,
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
    second_mate.promote_direction(repository, candidate.to_json(), _approval(candidate))
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
