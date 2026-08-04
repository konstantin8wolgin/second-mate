from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from test_preflight import make_repository, run_git, target_snapshot

from second_mate.store import strict_json_loads

FIXTURES = Path(__file__).parent / "fixtures"


def run_cli(*arguments: str) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-m", "second_mate", *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    document = strict_json_loads(completed.stdout)
    assert isinstance(document, dict)
    return document


def write_json(path: Path, document: dict[str, object]) -> None:
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def authority_documents(
    candidate: dict[str, object], *, suffix: str
) -> tuple[dict[str, object], dict[str, object]]:
    candidate_body = candidate["candidate"]
    basis = candidate["promotion_basis"]
    assert isinstance(candidate_body, dict)
    assert isinstance(basis, dict)
    digest = candidate["candidate_digest"]
    approval = {
        "schema_version": 1,
        "id": f"direction-approval-{suffix}",
        "decision": "approved",
        "direction_id": candidate_body["id"],
        "candidate_digest": digest,
        "approved_by": "project-owner",
        "approved_at": f"2026-08-04T11:0{suffix}:00Z",
    }
    grant = {
        "schema_version": 1,
        "id": f"direction-promotion-{suffix}",
        "granted_by": "project-owner",
        "granted_at": f"2026-08-04T11:1{suffix}:00Z",
        "candidate_digest": digest,
        "target_head": basis["target_head"],
        "target_fingerprint": basis["target_fingerprint"],
        "run_state_sha256": basis["run_state_sha256"],
        "allowed_paths": [".second-mate/directions.json"],
        "allowed_effects": ["direction_ledger_write"],
        "stop_conditions": ["revision_drift", "direction_history_drift", "open_run"],
    }
    return approval, grant


def promote_cli(
    target: Path,
    control: Path,
    summary: Path,
    *,
    direction_id: str,
    suffix: str,
    change_note: str | None = None,
) -> dict[str, object]:
    prepare_arguments = [
        "direction",
        "prepare",
        "--target",
        os.fspath(target),
        "--summary",
        os.fspath(summary),
        "--id",
        direction_id,
    ]
    if change_note is not None:
        prepare_arguments.extend(("--change-note", change_note))
    candidate = run_cli(*prepare_arguments)
    candidate_path = control / f"{direction_id}-candidate.json"
    approval_path = control / f"{direction_id}-approval.json"
    grant_path = control / f"{direction_id}-grant.json"
    write_json(candidate_path, candidate)
    approval, grant = authority_documents(candidate, suffix=suffix)
    write_json(approval_path, approval)
    write_json(grant_path, grant)
    return run_cli(
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


def test_d01_cli_journey_is_read_only_until_promotion_and_feeds_existing_draft(
    tmp_path: Path,
) -> None:
    target = make_repository(tmp_path)
    control = tmp_path / "control"
    control.mkdir()
    before = target_snapshot(target)
    candidate = run_cli(
        "direction",
        "prepare",
        "--target",
        os.fspath(target),
        "--summary",
        os.fspath(FIXTURES / "direction_operator" / "d01.md"),
        "--id",
        "D-01",
    )
    assert target_snapshot(target) == before
    candidate_path = control / "D-01-candidate.json"
    approval_path = control / "D-01-approval.json"
    grant_path = control / "D-01-grant.json"
    write_json(candidate_path, candidate)
    approval, grant = authority_documents(candidate, suffix="1")
    write_json(approval_path, approval)
    write_json(grant_path, grant)

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
    shown = run_cli("direction", "show", "--target", os.fspath(target))
    direction_path = control / "direction.json"
    write_json(direction_path, shown)
    draft = run_cli(
        "draft",
        "--direction",
        os.fspath(direction_path),
        "--packet",
        os.fspath(FIXTURES / "fs01_operator" / "packet.json"),
    )

    assert shown["id"] == "D-01"
    assert draft["direction"] == shown
    assert draft["packet"]["direction_id"] == "D-01"


def test_d02_cli_journey_appends_history_that_is_readable_from_a_clone(tmp_path: Path) -> None:
    target = make_repository(tmp_path)
    control = tmp_path / "control"
    control.mkdir()
    d01 = promote_cli(
        target,
        control,
        FIXTURES / "direction_operator" / "d01.md",
        direction_id="D-01",
        suffix="1",
    )
    d02 = promote_cli(
        target,
        control,
        FIXTURES / "direction_operator" / "d02.md",
        direction_id="D-02",
        suffix="2",
        change_note="Add the portable evidence boundary approved by the owner.",
    )

    assert run_cli("direction", "show", "--target", os.fspath(target))["id"] == "D-02"
    assert (
        run_cli("direction", "show", "--target", os.fspath(target), "--id", "D-01")
        == d01["direction"]
    )
    ledger_path = target / ".second-mate" / "directions.json"
    assert str(target) not in ledger_path.read_text(encoding="utf-8")
    run_git(target, "add", ".second-mate/directions.json")
    run_git(target, "commit", "-q", "-m", "record approved Direction history")
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", os.fspath(target), os.fspath(clone)], check=True)

    assert run_cli("direction", "show", "--target", os.fspath(clone)) == d02["direction"]
    assert (
        run_cli("direction", "show", "--target", os.fspath(clone), "--id", "D-01")
        == d01["direction"]
    )
