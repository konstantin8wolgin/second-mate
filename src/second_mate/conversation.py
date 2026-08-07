"""Provider-free preparation of reviewable First Mate conversation handoffs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from second_mate.direction import (
    DirectionCandidateEnvelope,
    find_direction_version,
    prepare_direction,
)
from second_mate.domain import JsonObject, ValidationError, digest_json

_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_TASK_KEYS = {
    "schema_version",
    "handoff_id",
    "source_conversation_id",
    "repository_id",
    "task",
    "assumptions",
    "allowed_effects",
    "prohibited_effects",
    "acceptance",
}
_CHANGE_NOTE = "Adopt the newly approved conversation-derived task."


def _object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValidationError(f"{label} must be a JSON object")
    return cast(dict[str, object], value)


def _schema_one(value: object, label: str) -> None:
    if type(value) is not int or value != 1:
        raise ValidationError(f"{label} schema_version must be the integer 1")


def _text(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{label} must be a string")
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise ValidationError(f"{label} must be non-empty")
    if "\x00" in normalized:
        raise ValidationError(f"{label} must not contain NUL")
    return normalized


def _identifier(value: object, label: str) -> str:
    result = _text(value, label)
    if not _IDENTIFIER.fullmatch(result):
        raise ValidationError(f"{label} must use only letters, numbers, dot, underscore, or hyphen")
    return result


def _texts(value: object, label: str, *, required: bool) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValidationError(f"{label} must be a list of strings")
    result = tuple(_text(item, f"{label} item") for item in value)
    if required and not result:
        raise ValidationError(f"{label} must not be empty")
    if len(result) != len(set(result)):
        raise ValidationError(f"{label} must not contain duplicates")
    return result


def _section(label: str, values: tuple[str, ...]) -> str:
    body = "\n".join(f"- {value}" for value in values) if values else "- None stated."
    return f"{label}:\n{body}"


@dataclass(frozen=True, slots=True)
class ConversationTask:
    """Normalized material task meaning, without raw conversation identity."""

    handoff_id: str
    repository_id: str
    task: str
    assumptions: tuple[str, ...]
    allowed_effects: tuple[str, ...]
    prohibited_effects: tuple[str, ...]
    acceptance: tuple[str, ...]

    def to_json(self) -> JsonObject:
        return {
            "acceptance": list(self.acceptance),
            "allowed_effects": list(self.allowed_effects),
            "assumptions": list(self.assumptions),
            "handoff_id": self.handoff_id,
            "prohibited_effects": list(self.prohibited_effects),
            "repository_id": self.repository_id,
            "schema_version": 1,
            "task": self.task,
        }


@dataclass(frozen=True, slots=True)
class ConversationReview:
    """Ordinary-language task and effect summary shown before approval."""

    task: str
    assumptions: tuple[str, ...]
    proposed_effects: tuple[str, ...]
    prohibited_effects: tuple[str, ...]
    acceptance: tuple[str, ...]
    execution_authorized: bool = False

    def to_json(self) -> JsonObject:
        return {
            "acceptance": list(self.acceptance),
            "assumptions": list(self.assumptions),
            "execution_authorized": self.execution_authorized,
            "prohibited_effects": list(self.prohibited_effects),
            "proposed_effects": list(self.proposed_effects),
            "task": self.task,
        }


@dataclass(frozen=True, slots=True)
class ConversationProposal:
    """Read-only, digest-bound review input to one later approval action."""

    task: ConversationTask
    source_binding_digest: str
    direction_candidate: DirectionCandidateEnvelope
    review: ConversationReview
    proposal_digest: str
    status: str = "awaiting-approval"
    summary: str = "Review this task. No run has started."
    next_action: str = "Approve the task meaning and one Direction-ledger write."

    def to_json(self) -> JsonObject:
        return {
            "direction_candidate": self.direction_candidate.to_json(),
            "next_action": self.next_action,
            "proposal_digest": self.proposal_digest,
            "review": self.review.to_json(),
            "schema_version": 1,
            "source_binding_digest": self.source_binding_digest,
            "status": self.status,
            "summary": self.summary,
            "task": self.task.to_json(),
        }


def _task_from_json(value: object) -> tuple[ConversationTask, str]:
    data = _object(value, "conversation handoff")
    if set(data) != _TASK_KEYS:
        raise ValidationError("conversation handoff fields do not match schema version 1")
    _schema_one(data["schema_version"], "conversation handoff")
    handoff_id = _identifier(data["handoff_id"], "conversation handoff handoff_id")
    repository_id = _identifier(data["repository_id"], "conversation handoff repository_id")
    source_conversation_id = _identifier(
        data["source_conversation_id"],
        "conversation handoff source_conversation_id",
    )
    task = ConversationTask(
        handoff_id=handoff_id,
        repository_id=repository_id,
        task=_text(data["task"], "conversation handoff task"),
        assumptions=_texts(data["assumptions"], "conversation handoff assumptions", required=False),
        allowed_effects=_texts(
            data["allowed_effects"],
            "conversation handoff allowed_effects",
            required=True,
        ),
        prohibited_effects=_texts(
            data["prohibited_effects"],
            "conversation handoff prohibited_effects",
            required=False,
        ),
        acceptance=_texts(data["acceptance"], "conversation handoff acceptance", required=True),
    )
    source_binding_digest = digest_json(
        {
            "handoff_id": handoff_id,
            "repository_id": repository_id,
            "source_conversation_id": source_conversation_id,
        }
    )
    return task, source_binding_digest


def _direction_id(task: ConversationTask) -> str:
    binding = digest_json({"handoff_id": task.handoff_id, "repository_id": task.repository_id})
    return f"D-CB-{binding[:20]}"


def _render_direction(task: ConversationTask) -> str:
    return (
        f"Outcome:\n{task.task}\n\n"
        f"{_section('Assumptions', task.assumptions)}\n\n"
        f"{_section('Proposed effects (not execution authority)', task.allowed_effects)}\n\n"
        f"{_section('Prohibited effects', task.prohibited_effects)}\n\n"
        f"{_section('Acceptance', task.acceptance)}\n\n"
        "Authority boundary:\n"
        "- Approval records task meaning and one Direction-ledger write only.\n"
        "- Route approval and Execution Consent are not granted.\n"
    )


def _review(task: ConversationTask) -> ConversationReview:
    return ConversationReview(
        task=task.task,
        assumptions=task.assumptions,
        proposed_effects=task.allowed_effects,
        prohibited_effects=task.prohibited_effects,
        acceptance=task.acceptance,
    )


def prepare_conversation_handoff(
    repository: Path,
    task_data: object,
) -> ConversationProposal:
    """Prepare a conversation-derived Direction candidate without writing the target."""
    task, source_binding_digest = _task_from_json(task_data)
    change_note = None if find_direction_version(repository) is None else _CHANGE_NOTE
    direction_candidate = prepare_direction(
        repository,
        _render_direction(task),
        direction_id=_direction_id(task),
        change_note=change_note,
    )
    review = _review(task)
    proposal_digest = digest_json(
        {
            "direction_candidate": direction_candidate.to_json(),
            "review": review.to_json(),
            "source_binding_digest": source_binding_digest,
            "task": task.to_json(),
        }
    )
    return ConversationProposal(
        task=task,
        source_binding_digest=source_binding_digest,
        direction_candidate=direction_candidate,
        review=review,
        proposal_digest=proposal_digest,
    )


__all__ = [
    "ConversationProposal",
    "ConversationReview",
    "ConversationTask",
    "prepare_conversation_handoff",
]
