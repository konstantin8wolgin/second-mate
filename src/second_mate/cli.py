"""Thin operator surface for the supervised FS-01 lifecycle."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from second_mate.domain import ValidationError, create_draft, draft_from_json
from second_mate.fixture import FixtureExecutor
from second_mate.repository import preflight, preflight_from_json
from second_mate.service import (
    AuthorityError,
    CloseFailure,
    ExecutionFailure,
    RunConflictError,
    clean_close,
    load_state,
    record_evidence,
    restart_run,
    start_run,
)
from second_mate.store import StateRecoveryError, deterministic_json_bytes


def _read_json(path: str) -> object:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValidationError(f"cannot read JSON document {path}: {error}") from error


def _emit(value: object) -> None:
    if not hasattr(value, "to_json"):
        raise TypeError("operator result is not a JSON document")
    document = value.to_json()
    sys.stdout.buffer.write(deterministic_json_bytes(document))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="second-mate",
        description="Operate one authority-bound deterministic Foundation Slice run.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    draft = subparsers.add_parser("draft", help="validate and freeze Direction plus packet")
    draft.add_argument("--direction", required=True)
    draft.add_argument("--packet", required=True)

    preflight_parser = subparsers.add_parser(
        "preflight", help="read the target basis without changing it"
    )
    preflight_parser.add_argument("--target", required=True)
    preflight_parser.add_argument("--draft", required=True)

    start = subparsers.add_parser("start", help="guard and dispatch one executor invocation")
    start.add_argument("--target", required=True)
    start.add_argument("--draft", required=True)
    start.add_argument("--preflight", required=True)
    start.add_argument("--grant", required=True)
    start.add_argument("--owner", required=True)
    start.add_argument("--executor", required=True, choices=("fixture",))

    restart = subparsers.add_parser("restart", help="resume only under the durable owner")
    restart.add_argument("--target", required=True)
    restart.add_argument("--owner", required=True)
    restart.add_argument("--executor", required=True, choices=("fixture",))

    evidence = subparsers.add_parser("evidence", help="record exact after-revision proof")
    evidence.add_argument("--target", required=True)

    close = subparsers.add_parser("close", help="perform recoverable claim-fit clean close")
    close.add_argument("--target", required=True)
    close.add_argument(
        "--direction-coverage",
        required=True,
        choices=("proven", "explicitly_deferred", "intentionally_changed", "still_remaining"),
    )
    close.add_argument("--residual-uncertainty", action="append", default=[])
    close.add_argument("--handoff", required=True)

    show = subparsers.add_parser("show", help="validate, recover if needed, and show state")
    show.add_argument("--target", required=True)
    return parser


def _run(args: argparse.Namespace) -> object:
    command = args.command
    if command == "draft":
        return create_draft(_read_json(args.direction), _read_json(args.packet))
    if command == "preflight":
        draft = draft_from_json(_read_json(args.draft))
        return preflight(draft, Path(args.target))
    if command == "start":
        draft = draft_from_json(_read_json(args.draft))
        basis = preflight_from_json(_read_json(args.preflight))
        return start_run(
            draft=draft,
            basis=basis,
            grant_data=_read_json(args.grant),
            repository=Path(args.target),
            executor=FixtureExecutor(),
            owner_id=args.owner,
        )
    if command == "restart":
        return restart_run(Path(args.target), FixtureExecutor(), owner_id=args.owner)
    if command == "evidence":
        return record_evidence(Path(args.target))
    if command == "close":
        return clean_close(
            Path(args.target),
            direction_coverage=args.direction_coverage,
            residual_uncertainty=tuple(args.residual_uncertainty),
            handoff=args.handoff,
        )
    if command == "show":
        return load_state(Path(args.target))
    raise AssertionError(f"unhandled operator command: {command}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the fixed FS-01 operator surface and return a process exit code."""
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        result = _run(args)
        _emit(result)
    except (
        AuthorityError,
        CloseFailure,
        ExecutionFailure,
        RunConflictError,
        StateRecoveryError,
        ValidationError,
        RuntimeError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return os.EX_OK
