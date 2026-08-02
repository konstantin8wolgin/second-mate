from __future__ import annotations

import copy
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


def approval(candidate: dict[str, Any], approval_id: str) -> dict[str, object]:
    return {
        "approved_at": "2026-08-02T12:00:00Z",
        "approved_by": "fixture-human",
        "candidate_digest": candidate["candidate_digest"],
        "decision": "approved",
        "direction_id": candidate["candidate"]["id"],
        "id": approval_id,
        "schema_version": 1,
    }


def promotion_grant(candidate: dict[str, Any], grant_id: str) -> dict[str, object]:
    basis = candidate["promotion_basis"]
    return {
        "allowed_effects": ["direction_ledger_write"],
        "allowed_paths": [".second-mate/directions.json"],
        "candidate_digest": candidate["candidate_digest"],
        "granted_at": "2026-08-02T12:01:00Z",
        "granted_by": "fixture-human",
        "id": grant_id,
        "schema_version": 1,
        "stop_conditions": ["revision_drift", "direction_history_drift"],
        "target_fingerprint": basis["target_fingerprint"],
        "target_head": basis["target_head"],
        "target_root": basis["target_root"],
    }


def snapshot(repository: Path) -> tuple[str, dict[str, bytes]]:
    files = {
        path.relative_to(repository).as_posix(): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repository).parts
    }
    return run_git(repository, "status", "--porcelain=v1"), files


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_external_rumble_summary_requires_approval_then_versions_durable_direction(
    tmp_path: Path,
) -> None:
    """Any silent promotion, mutable version, or draft disconnect must break this journey."""
    target = tmp_path / "target"
    control = tmp_path / "private-control"
    shutil.copytree(FIXTURES / "rumble_direction_target", target)
    control.mkdir()
    run_git(target, "init", "-q")
    run_git(target, "add", ".")
    run_git(target, "commit", "-q", "-m", "Rumble Direction fixture")
    before = snapshot(target)

    prepared = run_cli(
        "direction",
        "prepare",
        "--target",
        os.fspath(target),
        "--summary",
        os.fspath(FIXTURES / "rumble_direction_operator" / "d01.md"),
        "--id",
        "D-01",
    )
    candidate = json.loads(prepared.stdout)
    candidate_path = control / "D-01.candidate.json"
    candidate_path.write_text(prepared.stdout, encoding="utf-8")
    assert candidate["candidate"]["text"] == (
        FIXTURES / "rumble_direction_operator" / "d01.md"
    ).read_text(encoding="utf-8")
    assert snapshot(target) == before
    assert not (target / ".second-mate").exists()

    denied_without_approval = run_cli(
        "direction",
        "promote",
        "--target",
        os.fspath(target),
        "--candidate",
        os.fspath(candidate_path),
        check=False,
    )
    assert denied_without_approval.returncode != 0
    assert snapshot(target) == before

    changed_after_review = copy.deepcopy(candidate)
    changed_after_review["candidate"]["text"] = "Meaning changed after review.\n"
    changed_path = control / "changed-after-review.json"
    write_json(changed_path, changed_after_review)
    approval_path = control / "D-01.approval.json"
    write_json(approval_path, approval(candidate, "DA-01"))
    denied_approval_only = run_cli(
        "direction",
        "promote",
        "--target",
        os.fspath(target),
        "--candidate",
        os.fspath(candidate_path),
        "--approval",
        os.fspath(approval_path),
        check=False,
    )
    assert denied_approval_only.returncode != 0
    assert snapshot(target) == before
    grant_path = control / "D-01.promotion-grant.json"
    write_json(grant_path, promotion_grant(candidate, "DPG-01"))
    denied_changed = run_cli(
        "direction",
        "promote",
        "--target",
        os.fspath(target),
        "--candidate",
        os.fspath(changed_path),
        "--approval",
        os.fspath(approval_path),
        "--grant",
        os.fspath(grant_path),
        check=False,
    )
    assert denied_changed.returncode != 0
    assert snapshot(target) == before

    run_cli(
        "direction",
        "promote",
        "--target",
        os.fspath(target),
        "--candidate",
        os.fspath(candidate_path),
        "--approval",
        os.fspath(approval_path),
        "--grant",
        os.fspath(grant_path),
    )
    ledger_path = target / ".second-mate" / "directions.json"
    first_entry = json.loads(ledger_path.read_bytes())["versions"][0]

    shown = run_cli("direction", "show", "--target", os.fspath(target))
    shown_path = control / "approved-direction.json"
    shown_path.write_text(shown.stdout, encoding="utf-8")
    drafted = json.loads(
        run_cli(
            "draft",
            "--direction",
            os.fspath(shown_path),
            "--packet",
            os.fspath(FIXTURES / "fs01_operator" / "packet.json"),
        ).stdout
    )
    assert drafted["direction"]["id"] == "D-01"

    prepared_v2 = run_cli(
        "direction",
        "prepare",
        "--target",
        os.fspath(target),
        "--summary",
        os.fspath(FIXTURES / "rumble_direction_operator" / "d02.md"),
        "--id",
        "D-02",
        "--change-note",
        "Make approved change history explicit.",
    )
    candidate_v2 = json.loads(prepared_v2.stdout)
    candidate_v2_path = control / "D-02.candidate.json"
    candidate_v2_path.write_text(prepared_v2.stdout, encoding="utf-8")
    approval_v2_path = control / "D-02.approval.json"
    write_json(approval_v2_path, approval(candidate_v2, "DA-02"))
    grant_v2_path = control / "D-02.promotion-grant.json"
    write_json(grant_v2_path, promotion_grant(candidate_v2, "DPG-02"))
    run_cli(
        "direction",
        "promote",
        "--target",
        os.fspath(target),
        "--candidate",
        os.fspath(candidate_v2_path),
        "--approval",
        os.fspath(approval_v2_path),
        "--grant",
        os.fspath(grant_v2_path),
    )

    ledger_bytes = ledger_path.read_bytes()
    ledger = json.loads(ledger_bytes)
    assert ledger["current_direction_id"] == "D-02"
    assert ledger["versions"][0] == first_entry
    assert ledger["versions"][1]["promotion_grant"]["allowed_effects"] == ["direction_ledger_write"]
    assert (
        json.loads(
            run_cli("direction", "show", "--target", os.fspath(target), "--id", "D-01").stdout
        )
        == first_entry["direction"]
    )
    assert b"RUMBLE_TRANSCRIPT_PRIVATE_FIXTURE_SECRET" not in ledger_bytes
    assert b"private_reasoning" not in ledger_bytes
