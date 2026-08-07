"""Thin operator surface for conversation intake and supervised packet lifecycles."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from second_mate.conversation import (
    approve_conversation_handoff,
    conversation_handoff_status,
    prepare_conversation_handoff,
)
from second_mate.direction import (
    DirectionConflictError,
    load_direction,
    prepare_direction,
    promote_direction,
)
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
from second_mate.store import (
    StateRecoveryError,
    StrictJsonError,
    deterministic_json_bytes,
    strict_json_loads,
)


def _read_json(path: str) -> object:
    try:
        return strict_json_loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, StrictJsonError) as error:
        raise ValidationError(f"cannot read JSON document {path}: {error}") from error


def _read_text(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValidationError(f"cannot read UTF-8 text document {path}: {error}") from error


def _emit(value: object) -> None:
    if not hasattr(value, "to_json"):
        raise TypeError("operator result is not a JSON document")
    document = value.to_json()
    sys.stdout.buffer.write(deterministic_json_bytes(document))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="second-mate",
        description="Operate approved Direction intake and one authority-bound Foundation run.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    draft = subparsers.add_parser("draft", help="validate and freeze Direction plus packet")
    draft.add_argument("--direction", required=True)
    draft.add_argument("--packet", required=True)

    handoff = subparsers.add_parser(
        "handoff",
        help="prepare, approve, or inspect a conversation-derived task without running it",
    )
    handoff_commands = handoff.add_subparsers(dest="handoff_command", required=True)
    handoff_prepare = handoff_commands.add_parser(
        "prepare",
        help="turn a First Mate task summary into a read-only review proposal",
    )
    handoff_prepare.add_argument("--target", required=True)
    handoff_prepare.add_argument("--input", required=True)
    handoff_approve = handoff_commands.add_parser(
        "approve",
        help="record task meaning and one Direction-ledger write; do not run",
    )
    handoff_approve.add_argument("--target", required=True)
    handoff_approve.add_argument("--proposal", required=True)
    handoff_approve.add_argument("--approval", required=True)
    handoff_status = handoff_commands.add_parser(
        "status",
        help="show whether an exact proposal is awaiting, ready, conflicting, or superseded",
    )
    handoff_status.add_argument("--target", required=True)
    handoff_status.add_argument("--proposal", required=True)

    direction = subparsers.add_parser(
        "direction", help="prepare, explicitly promote, or show Direction versions"
    )
    direction_commands = direction.add_subparsers(dest="direction_command", required=True)
    direction_prepare = direction_commands.add_parser(
        "prepare", help="freeze an editable summary without changing the target"
    )
    direction_prepare.add_argument("--target", required=True)
    direction_prepare.add_argument("--summary", required=True)
    direction_prepare.add_argument("--id", required=True)
    direction_prepare.add_argument("--change-note")
    direction_promote = direction_commands.add_parser(
        "promote", help="validate exact human approval and append durable Direction"
    )
    direction_promote.add_argument("--target", required=True)
    direction_promote.add_argument("--candidate", required=True)
    direction_promote.add_argument("--approval", required=True)
    direction_promote.add_argument("--grant", required=True)
    direction_show = direction_commands.add_parser(
        "show", help="show a validated approved Direction for downstream use"
    )
    direction_show.add_argument("--target", required=True)
    direction_show.add_argument("--id")

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
    if command == "handoff":
        handoff_command = args.handoff_command
        if handoff_command == "prepare":
            return prepare_conversation_handoff(
                Path(args.target),
                _read_json(args.input),
            )
        if handoff_command == "approve":
            return approve_conversation_handoff(
                Path(args.target),
                _read_json(args.proposal),
                _read_json(args.approval),
            )
        if handoff_command == "status":
            return conversation_handoff_status(
                Path(args.target),
                _read_json(args.proposal),
            )
        raise AssertionError(f"unhandled handoff command: {handoff_command}")
    if command == "direction":
        direction_command = args.direction_command
        if direction_command == "prepare":
            return prepare_direction(
                Path(args.target),
                _read_text(args.summary),
                direction_id=args.id,
                change_note=args.change_note,
            )
        if direction_command == "promote":
            return promote_direction(
                Path(args.target),
                _read_json(args.candidate),
                _read_json(args.approval),
                _read_json(args.grant),
            )
        if direction_command == "show":
            return load_direction(Path(args.target), args.id)
        raise AssertionError(f"unhandled Direction command: {direction_command}")
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
    """Run the fixed operator surfaces and return a process exit code."""
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        result = _run(args)
        _emit(result)
    except (
        AuthorityError,
        CloseFailure,
        DirectionConflictError,
        ExecutionFailure,
        RunConflictError,
        StateRecoveryError,
        ValidationError,
        RuntimeError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return os.EX_OK
