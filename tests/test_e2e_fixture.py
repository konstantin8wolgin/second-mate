from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
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


def test_cli_rejects_ambiguous_duplicate_authority_fields(tmp_path: Path) -> None:
    """Last-key-wins JSON decoding must not reinterpret a reviewed authority document."""
    direction_path = tmp_path / "direction.json"
    source = (FIXTURES / "fs01_operator" / "direction.json").read_text(encoding="utf-8")
    marker = '  "schema_version": 1'
    assert source.count(marker) == 1
    direction_path.write_text(
        source.replace(marker, '  "schema_version": 999,\n' + marker),
        encoding="utf-8",
    )

    denied = run_cli(
        "draft",
        "--direction",
        os.fspath(direction_path),
        "--packet",
        os.fspath(FIXTURES / "fs01_operator" / "packet.json"),
        check=False,
    )

    assert denied.returncode != 0
    assert "duplicate JSON object field: schema_version" in denied.stderr


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
            "--residual-uncertainty",
            "Human product review remains outstanding.",
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


@pytest.mark.parametrize("alias_kind", ("symlink", "hardlink"))
def test_cli_refuses_aliased_artifact_before_out_of_boundary_mutation(
    tmp_path: Path,
    alias_kind: str,
) -> None:
    """The allowed path must not alias its write to another repository file."""
    target = tmp_path / "target"
    control = tmp_path / "control"
    shutil.copytree(FIXTURES / "fs01_target", target)
    control.mkdir()
    redirected = target / "redirected.txt"
    redirected.write_text("before\n", encoding="utf-8")
    (target / "artifact.txt").unlink()
    if alias_kind == "symlink":
        (target / "artifact.txt").symlink_to(redirected.name)
    else:
        os.link(redirected, target / "artifact.txt")
    run_git(target, "init", "-q")
    run_git(target, "add", ".")
    run_git(target, "commit", "-q", "-m", "symlinked FS-01 fixture")

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

    denied = run_cli(
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
        check=False,
    )

    assert denied.returncode != 0
    assert basis["preflight"]["eligible"] is False
    assert redirected.read_text(encoding="utf-8") == "before\n"
    assert not (target / ".second-mate").exists()


@pytest.mark.parametrize(
    "reserved_name",
    (
        "state.json.next",
        "state.json.pending.next",
        f"state.json.next.{'0' * 64}",
        f"state.json.pending.next.{'0' * 64}",
    ),
)
@pytest.mark.parametrize("tracked_collision", (False, True))
def test_cli_preflight_refuses_preexisting_coordinator_scratch_collisions(
    tmp_path: Path,
    reserved_name: str,
    tracked_collision: bool,
) -> None:
    """A reserved pathname is not evidence that the coordinator owns its content."""
    target = tmp_path / "target"
    control = tmp_path / "control"
    shutil.copytree(FIXTURES / "fs01_target", target)
    control.mkdir()
    run_git(target, "init", "-q")
    run_git(target, "add", ".")
    run_git(target, "commit", "-q", "-m", "fixture baseline")
    state_directory = target / ".second-mate"
    state_directory.mkdir()
    collision = state_directory / reserved_name
    collision.write_text("pre-existing target content\n", encoding="utf-8")
    if tracked_collision:
        run_git(target, "add", os.fspath(collision.relative_to(target)))
        run_git(target, "commit", "-q", "-m", "track reserved path collision")

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

    denied = run_cli(
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
        check=False,
    )

    assert basis["preflight"]["eligible"] is False
    assert denied.returncode != 0
    assert collision.read_text(encoding="utf-8") == "pre-existing target content\n"
    assert (target / "artifact.txt").read_text(encoding="utf-8") == "before\n"
    assert not (state_directory / "state.json").exists()


def test_cli_refuses_a_state_directory_symlink_before_external_state_write(
    tmp_path: Path,
) -> None:
    """Coordinator state must not escape the target through a pre-existing symlink."""
    target = tmp_path / "target"
    control = tmp_path / "control"
    escaped_state = tmp_path / "escaped-state"
    shutil.copytree(FIXTURES / "fs01_target", target)
    control.mkdir()
    escaped_state.mkdir()
    (target / ".second-mate").symlink_to(escaped_state, target_is_directory=True)
    run_git(target, "init", "-q")
    run_git(target, "add", ".")
    run_git(target, "commit", "-q", "-m", "fixture with redirected state directory")

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

    denied = run_cli(
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
        check=False,
    )

    assert denied.returncode != 0
    assert basis["preflight"]["eligible"] is False
    assert (target / "artifact.txt").read_text(encoding="utf-8") == "before\n"
    assert list(escaped_state.iterdir()) == []


@pytest.mark.parametrize("alias_kind", ("symlink", "hardlink"))
def test_cli_preflight_rejects_an_aliased_applicable_instruction(
    tmp_path: Path,
    alias_kind: str,
) -> None:
    """An ignored instruction alias cannot freeze the authority text it shares."""
    target = tmp_path / "target"
    control = tmp_path / "control"
    shutil.copytree(FIXTURES / "fs01_target", target)
    control.mkdir()
    (target / "AGENTS.md").unlink()
    (target / ".local-instructions.md").write_text(
        "Only artifact.txt may change.\n", encoding="utf-8"
    )
    if alias_kind == "symlink":
        (target / "AGENTS.md").symlink_to(".local-instructions.md")
    else:
        os.link(target / ".local-instructions.md", target / "AGENTS.md")
    (target / ".gitignore").write_text("AGENTS.md\n.local-instructions.md\n", encoding="utf-8")
    run_git(target, "init", "-q")
    run_git(target, "add", ".")
    run_git(target, "commit", "-q", "-m", "fixture with local instruction symlink")

    draft_result = run_cli(
        "draft",
        "--direction",
        os.fspath(FIXTURES / "fs01_operator" / "direction.json"),
        "--packet",
        os.fspath(FIXTURES / "fs01_operator" / "packet.json"),
    )
    draft_path = control / "draft.json"
    draft_path.write_text(draft_result.stdout, encoding="utf-8")

    denied_preflight = run_cli(
        "preflight",
        "--target",
        os.fspath(target),
        "--draft",
        os.fspath(draft_path),
        check=False,
    )

    assert denied_preflight.returncode != 0
    assert "applicable instruction must be a regular file" in denied_preflight.stderr
    assert (target / "artifact.txt").read_text(encoding="utf-8") == "before\n"
    assert not (target / ".second-mate").exists()


@pytest.mark.parametrize(
    "unsupported_coverage", ("proven", "explicitly_deferred", "intentionally_changed")
)
def test_cli_refuses_unsupported_fixture_direction_coverage(
    tmp_path: Path,
    unsupported_coverage: str,
) -> None:
    """FS-01 has neither linked proof nor human change authority for broader coverage."""
    target, _ = start_fixture_run(tmp_path, ignore_agents=False)
    evidence = json.loads(run_cli("evidence", "--target", os.fspath(target)).stdout)
    assert evidence["evidence"][-1]["result"] == "pass"

    denied_close = run_cli(
        "close",
        "--target",
        os.fspath(target),
        "--direction-coverage",
        unsupported_coverage,
        "--residual-uncertainty",
        "Live provider behavior was not exercised.",
        "--handoff",
        "Fixture completion cannot prove the broader Direction.",
        check=False,
    )

    assert denied_close.returncode != 0
    durable = json.loads(run_cli("show", "--target", os.fspath(target)).stdout)
    assert durable["closed"] is False
    assert durable["route_status"] == "ready"
    assert durable["direction_coverage"] == "still_remaining"
    assert durable["run"]["phase"] == "ready_to_close"


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


@pytest.mark.parametrize("inspection_failure", ("instruction-alias", "revision-entry"))
def test_cli_retains_unsafe_inspection_as_failed_evidence_before_repair(
    tmp_path: Path,
    inspection_failure: str,
) -> None:
    target, _ = start_fixture_run(tmp_path, ignore_agents=True)
    if inspection_failure == "instruction-alias":
        damaged = target / "AGENTS.md"
        original = damaged.read_bytes()
        external = tmp_path / "external-instructions.md"
        external.write_bytes(original)
        damaged.unlink()
        damaged.symlink_to(external)
    else:
        damaged = target / "probe.py"
        original = damaged.read_bytes()
        damaged.unlink()
        damaged.mkdir()

    failed = json.loads(run_cli("evidence", "--target", os.fspath(target)).stdout)

    assert failed["run"]["phase"] == "evidence_failed"
    assert failed["evidence"][-1]["result"] == "fail"
    assert any(
        "could not be safely inspected" in item
        for item in failed["evidence"][-1]["observation"]["failures"]
    )
    durable_failure = json.loads(run_cli("show", "--target", os.fspath(target)).stdout)
    assert [item["result"] for item in durable_failure["evidence"]] == ["fail"]

    if damaged.is_symlink():
        damaged.unlink()
    else:
        damaged.rmdir()
    damaged.write_bytes(original)
    repaired = json.loads(run_cli("evidence", "--target", os.fspath(target)).stdout)

    assert repaired["run"]["phase"] == "ready_to_close"
    assert [item["result"] for item in repaired["evidence"]] == ["fail", "pass"]


def test_cli_rejects_unrelated_target_drift_between_dispatch_and_evidence(
    tmp_path: Path,
) -> None:
    """Removing the exact-after target comparison must make this journey fail."""
    target, _ = start_fixture_run(tmp_path, ignore_agents=False)
    (target / "unrelated.txt").write_text("outside the grant\n", encoding="utf-8")

    evidence = json.loads(run_cli("evidence", "--target", os.fspath(target)).stdout)

    assert evidence["evidence"][-1]["result"] == "fail"
    assert evidence["evidence"][-1]["observation"]["target_revision_matches_authority"] is False
    durable = json.loads(run_cli("show", "--target", os.fspath(target)).stdout)
    assert durable["closed"] is False
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


def test_cli_rejects_unrelated_target_drift_after_passing_evidence(tmp_path: Path) -> None:
    """Removing the close-time live target guard must make this journey fail."""
    target, _ = start_fixture_run(tmp_path, ignore_agents=False)
    evidence = json.loads(run_cli("evidence", "--target", os.fspath(target)).stdout)
    assert evidence["evidence"][-1]["result"] == "pass"
    (target / "unrelated.txt").write_text("outside the grant\n", encoding="utf-8")

    denied_close = run_cli(
        "close",
        "--target",
        os.fspath(target),
        "--direction-coverage",
        "still_remaining",
        "--handoff",
        "Target drift after evidence must block close.",
        check=False,
    )

    assert denied_close.returncode != 0
    durable = json.loads(run_cli("show", "--target", os.fspath(target)).stdout)
    assert durable["closed"] is False
    assert durable["route_status"] == "ready"
    assert durable["run"]["phase"] == "ready_to_close"
    assert durable["evidence"][-1]["result"] == "pass"
