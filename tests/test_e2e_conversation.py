from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from test_preflight import make_repository, target_snapshot

from second_mate.store import strict_json_loads

FIXTURE = Path(__file__).parent / "fixtures" / "conversation_operator" / "task.json"


def _run_cli(*arguments: str) -> tuple[str, dict[str, object]]:
    completed = subprocess.run(
        [sys.executable, "-m", "second_mate", *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    document = strict_json_loads(completed.stdout)
    assert isinstance(document, dict)
    return completed.stdout, document


def _write_json(path: Path, document: dict[str, object]) -> None:
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _approval(proposal: dict[str, object]) -> dict[str, object]:
    candidate = proposal["direction_candidate"]
    assert isinstance(candidate, dict)
    return {
        "schema_version": 1,
        "id": "approve-conversation-task-17",
        "decision": "approved",
        "proposal_digest": proposal["proposal_digest"],
        "candidate_digest": candidate["candidate_digest"],
        "approved_by": "project-owner",
        "approved_at": "2026-08-07T10:00:00Z",
        "approved_scopes": ["direction_meaning", "direction_ledger_write"],
    }


def test_first_mate_handoff_cli_is_readable_idempotent_and_stops_before_run(
    tmp_path: Path,
) -> None:
    """The internal transport must support ordinary review/approve without dispatch."""
    target = make_repository(tmp_path)
    control = tmp_path / "control"
    control.mkdir()
    before = target_snapshot(target)

    _, proposal = _run_cli(
        "handoff",
        "prepare",
        "--target",
        os.fspath(target),
        "--input",
        os.fspath(FIXTURE),
    )

    assert target_snapshot(target) == before
    assert proposal["status"] == "awaiting-approval"
    assert proposal["summary"] == "Review this task. No run has started."
    assert "conversation-42" not in repr(proposal)
    proposal_path = control / "proposal.json"
    approval_path = control / "approval.json"
    _write_json(proposal_path, proposal)
    _write_json(approval_path, _approval(proposal))

    first_stdout, first = _run_cli(
        "handoff",
        "approve",
        "--target",
        os.fspath(target),
        "--proposal",
        os.fspath(proposal_path),
        "--approval",
        os.fspath(approval_path),
    )
    ledger_path = target / ".second-mate" / "directions.json"
    first_ledger = ledger_path.read_bytes()
    first_metadata = ledger_path.stat()
    second_stdout, second = _run_cli(
        "handoff",
        "approve",
        "--target",
        os.fspath(target),
        "--proposal",
        os.fspath(proposal_path),
        "--approval",
        os.fspath(approval_path),
    )

    assert first_stdout == second_stdout
    assert first == second
    assert first["status"] == "ready-for-preflight"
    assert first["execution_authorized"] is False
    assert ledger_path.read_bytes() == first_ledger
    assert ledger_path.stat().st_ino == first_metadata.st_ino
    assert ledger_path.stat().st_mtime_ns == first_metadata.st_mtime_ns

    _, status = _run_cli(
        "handoff",
        "status",
        "--target",
        os.fspath(target),
        "--proposal",
        os.fspath(proposal_path),
    )
    assert status["status"] == "ready-for-preflight"
    assert status["execution_authorized"] is False

    help_result = subprocess.run(
        [sys.executable, "-m", "second_mate", "handoff", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert help_result.returncode == 0, help_result.stderr
    assert "{prepare,approve,status}" in help_result.stdout
    assert not any(line.strip().startswith("run ") for line in help_result.stdout.splitlines())
