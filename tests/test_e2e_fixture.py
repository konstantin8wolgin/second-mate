from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from test_preflight import run_git

FIXTURES = Path(__file__).parent / "fixtures"


def run_cli(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "second_mate", *args],
        check=check,
        capture_output=True,
        text=True,
    )


def fixture_grant(draft: dict[str, Any], basis: dict[str, Any]) -> dict[str, Any]:
    packet = draft["packet"]
    preflight = basis["preflight"]
    return {
        "allowed_effects": packet["boundary"]["allowed_effects"],
        "allowed_paths": packet["boundary"]["allowed_paths"],
        "direction_digest": draft["direction_digest"],
        "direction_id": draft["direction"]["id"],
        "granted_at": "2026-08-02T10:05:00Z",
        "granted_by": "fixture-human",
        "id": "grant-1",
        "packet_digest": draft["packet_digest"],
        "preflight_digest": basis["preflight_digest"],
        "repository_id": packet["repository_id"],
        "schema_version": 1,
        "stop_conditions": packet["boundary"]["stop_conditions"],
        "target_fingerprint": preflight["revision"]["fingerprint"],
        "target_head": preflight["revision"]["head"],
    }


def start_fixture_run(tmp_path: Path, *, ignore_agents: bool) -> tuple[Path, dict[str, Any]]:
    target = tmp_path / "target"
    control = tmp_path / "control"
    shutil.copytree(FIXTURES / "fs01_target", target)
    control.mkdir()
    if ignore_agents:
        (target / ".gitignore").write_text("AGENTS.md\n", encoding="utf-8")
    run_git(target, "init", "-q")
    run_git(target, "add", ".")
    run_git(target, "commit", "-q", "-m", "permanent FS-01 fixture")

    draft_result = run_cli(
        "draft",
        "--direction",
        os.fspath(FIXTURES / "fs01_operator" / "direction.json"),
        "--packet",
        os.fspath(FIXTURES / "fs01_operator" / "packet.json"),
    )
    draft_path = control / "draft.json"
    draft_path.write_text(draft_result.stdout, encoding="utf-8")
    draft = json.loads(draft_result.stdout)
    preflight_result = run_cli(
        "preflight", "--target", os.fspath(target), "--draft", os.fspath(draft_path)
    )
    preflight_path = control / "preflight.json"
    preflight_path.write_text(preflight_result.stdout, encoding="utf-8")
    basis = json.loads(preflight_result.stdout)
    grant_path = control / "grant.json"
    grant_path.write_text(
        json.dumps(fixture_grant(draft, basis), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    run_cli(
        "start",
        "--target",
        os.fspath(target),
        "--draft",
        os.fspath(draft_path),
        "--preflight",
        os.fspath(preflight_path),
        "--grant",
        os.fspath(grant_path),
        "--owner",
        "owner-1",
        "--executor",
        "fixture",
    )
    return target, basis


def test_clean_fixture_cli_replays_refusal_execution_evidence_and_close(tmp_path: Path) -> None:
    """Any CLI bypass or missing integrated lifecycle transition must break this clean replay."""
    target = tmp_path / "target"
    control = tmp_path / "control"
    shutil.copytree(FIXTURES / "fs01_target", target)
    control.mkdir()
    run_git(target, "init", "-q")
    run_git(target, "add", ".")
    run_git(target, "commit", "-q", "-m", "permanent FS-01 fixture")
    before_probe = subprocess.run(
        [sys.executable, os.fspath(target / "probe.py")],
        cwd=target,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert json.loads(before_probe)["artifact"] == "before\n"
    sentinel_before = (target / "sentinel.txt").read_bytes()

    draft_result = run_cli(
        "draft",
        "--direction",
        os.fspath(FIXTURES / "fs01_operator" / "direction.json"),
        "--packet",
        os.fspath(FIXTURES / "fs01_operator" / "packet.json"),
    )
    draft_path = control / "draft.json"
    draft_path.write_text(draft_result.stdout, encoding="utf-8")
    draft = json.loads(draft_result.stdout)

    preflight_result = run_cli(
        "preflight", "--target", os.fspath(target), "--draft", os.fspath(draft_path)
    )
    preflight_path = control / "preflight.json"
    preflight_path.write_text(preflight_result.stdout, encoding="utf-8")
    basis = json.loads(preflight_result.stdout)
    assert basis["preflight"]["affected_baseline"]["result"] == "pass"
    assert not (target / ".second-mate").exists()

    denied = run_cli(
        "start",
        "--target",
        os.fspath(target),
        "--draft",
        os.fspath(draft_path),
        "--preflight",
        os.fspath(preflight_path),
        "--owner",
        "owner-1",
        "--executor",
        "fixture",
        check=False,
    )
    assert denied.returncode != 0
    assert (target / "artifact.txt").read_text(encoding="utf-8") == "before\n"
    assert not (target / ".second-mate").exists()

    grant_path = control / "grant.json"
    grant_path.write_text(
        json.dumps(fixture_grant(draft, basis), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    started = run_cli(
        "start",
        "--target",
        os.fspath(target),
        "--draft",
        os.fspath(draft_path),
        "--preflight",
        os.fspath(preflight_path),
        "--grant",
        os.fspath(grant_path),
        "--owner",
        "owner-1",
        "--executor",
        "fixture",
    )
    assert json.loads(started.stdout)["run"]["attempts"] == 1

    after_probe = subprocess.run(
        [sys.executable, os.fspath(target / "probe.py")],
        cwd=target,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert json.loads(after_probe)["artifact"] == "after\n"
    assert (target / "sentinel.txt").read_bytes() == sentinel_before

    evidence = json.loads(run_cli("evidence", "--target", os.fspath(target)).stdout)
    assert evidence["evidence"][0]["result"] == "pass"
    closed = json.loads(
        run_cli(
            "close",
            "--target",
            os.fspath(target),
            "--direction-coverage",
            "still_remaining",
            "--residual-uncertainty",
            "Live provider behavior was not exercised.",
            "--handoff",
            "FS-01 is closed; human product review remains.",
        ).stdout
    )
    assert closed["closed"] is True
    assert closed["route_status"] == "completed"
    assert closed["direction_coverage"] == "still_remaining"
    assert closed["evidence"][0]["result"] == "pass"
    state_bytes = (target / ".second-mate" / "state.json").read_bytes()
    assert b"FIXTURE_SECRET_DO_NOT_COPY" not in state_bytes
    assert run_git(target, "diff", "--", "sentinel.txt", "probe.py") == ""


def test_cli_rejects_instruction_drift_between_dispatch_and_evidence(tmp_path: Path) -> None:
    """Certifying a changed ignored instruction must fail the final-authority journey."""
    target, basis = start_fixture_run(tmp_path, ignore_agents=True)
    instruction_paths = [item["path"] for item in basis["preflight"]["instructions"]]
    revision_paths = [item["path"] for item in basis["preflight"]["revision"]["files"]]
    assert "AGENTS.md" in instruction_paths
    assert "AGENTS.md" not in revision_paths
    (target / "AGENTS.md").write_text("Instructions changed after dispatch.\n", encoding="utf-8")

    evidence = json.loads(run_cli("evidence", "--target", os.fspath(target)).stdout)

    assert evidence["evidence"][0]["result"] == "fail"
    assert evidence["evidence"][0]["observation"]["instructions_match_preflight"] is False
    denied_close = run_cli(
        "close",
        "--target",
        os.fspath(target),
        "--direction-coverage",
        "still_remaining",
        "--handoff",
        "Instruction drift must be repaired before close.",
        check=False,
    )
    assert denied_close.returncode != 0
    durable = json.loads(run_cli("show", "--target", os.fspath(target)).stdout)
    assert durable["closed"] is False
    assert durable["route_status"] == "ready"
    assert durable["run"]["phase"] == "evidence_failed"


def test_cli_rejects_ignored_instruction_drift_after_passing_evidence(tmp_path: Path) -> None:
    """Removing the close-time live instruction guard must make this journey fail."""
    target, _ = start_fixture_run(tmp_path, ignore_agents=True)
    evidence = json.loads(run_cli("evidence", "--target", os.fspath(target)).stdout)
    assert evidence["evidence"][-1]["result"] == "pass"
    (target / "AGENTS.md").write_text("Instructions changed after evidence.\n", encoding="utf-8")

    denied_close = run_cli(
        "close",
        "--target",
        os.fspath(target),
        "--direction-coverage",
        "still_remaining",
        "--handoff",
        "Instruction drift after evidence must block close.",
        check=False,
    )

    assert denied_close.returncode != 0
    durable = json.loads(run_cli("show", "--target", os.fspath(target)).stdout)
    assert durable["closed"] is False
    assert durable["route_status"] == "ready"
    assert durable["run"]["phase"] == "ready_to_close"
    assert durable["evidence"][-1]["result"] == "pass"
