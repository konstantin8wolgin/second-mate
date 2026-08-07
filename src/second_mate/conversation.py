"""Provider-free preparation of reviewable First Mate conversation handoffs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from second_mate.direction import (
    ApprovedDirectionVersion,
    DirectionApproval,
    DirectionCandidateEnvelope,
    DirectionConflictError,
    PromotionGrant,
    find_direction_version,
    parse_direction_candidate,
    prepare_direction,
    promote_direction,
    require_direction_promotion_idle,
)
from second_mate.domain import Approval, Direction, JsonObject, ValidationError, digest_json

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
_TASK_OUTPUT_KEYS = {
    "schema_version",
    "handoff_id",
    "repository_id",
    "task",
    "assumptions",
    "allowed_effects",
    "prohibited_effects",
    "acceptance",
}
_REVIEW_KEYS = {
    "task",
    "assumptions",
    "proposed_effects",
    "prohibited_effects",
    "acceptance",
    "execution_authorized",
}
_PROPOSAL_KEYS = {
    "schema_version",
    "task",
    "source_binding_digest",
    "direction_candidate",
    "review",
    "proposal_digest",
    "status",
    "summary",
    "next_action",
}
_APPROVAL_KEYS = {
    "schema_version",
    "id",
    "decision",
    "proposal_digest",
    "candidate_digest",
    "approved_by",
    "approved_at",
    "approved_scopes",
}
_APPROVED_SCOPES = ("direction_meaning", "direction_ledger_write")
_AWAITING_SUMMARY = "Review this task. No run has started."
_AWAITING_NEXT_ACTION = "Approve the task meaning and one Direction-ledger write."


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


def _sha256(value: object, label: str) -> str:
    result = _text(value, label)
    if not re.fullmatch(r"[0-9a-f]{64}", result):
        raise ValidationError(f"{label} must be a lowercase SHA-256 digest")
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
    summary: str = _AWAITING_SUMMARY
    next_action: str = _AWAITING_NEXT_ACTION

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


@dataclass(frozen=True, slots=True)
class ConversationApprovalAction:
    """One visible approval action with two fixed non-execution scopes."""

    id: str
    proposal_digest: str
    candidate_digest: str
    approved_by: str
    approved_at: str
    approved_scopes: tuple[str, ...] = _APPROVED_SCOPES

    def to_json(self) -> JsonObject:
        return {
            "approved_at": self.approved_at,
            "approved_by": self.approved_by,
            "approved_scopes": list(self.approved_scopes),
            "candidate_digest": self.candidate_digest,
            "decision": "approved",
            "id": self.id,
            "proposal_digest": self.proposal_digest,
            "schema_version": 1,
        }


@dataclass(frozen=True, slots=True)
class AuthorityReceipt:
    """Human-readable status plus the exact machine record, when one exists."""

    kind: str
    status: str
    summary: str
    record_id: str | None
    record: JsonObject | None

    def to_json(self) -> JsonObject:
        return {
            "kind": self.kind,
            "record": self.record,
            "record_id": self.record_id,
            "status": self.status,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class HandoffAuthority:
    """The two recorded scopes and the two explicitly absent execution scopes."""

    direction_approval: AuthorityReceipt
    ledger_write_grant: AuthorityReceipt
    route_approval: AuthorityReceipt
    execution_consent: AuthorityReceipt

    def to_json(self) -> JsonObject:
        return {
            "direction_approval": self.direction_approval.to_json(),
            "execution_consent": self.execution_consent.to_json(),
            "ledger_write_grant": self.ledger_write_grant.to_json(),
            "route_approval": self.route_approval.to_json(),
        }


@dataclass(frozen=True, slots=True)
class RunIntent:
    """Approved task meaning for a later facade, without any execution facts."""

    repository_id: str
    direction_id: str
    direction_digest: str
    proposal_digest: str
    task: str
    assumptions: tuple[str, ...]
    requested_effects: tuple[str, ...]
    prohibited_effects: tuple[str, ...]
    acceptance: tuple[str, ...]

    def to_json(self) -> JsonObject:
        return {
            "acceptance": list(self.acceptance),
            "assumptions": list(self.assumptions),
            "direction_digest": self.direction_digest,
            "direction_id": self.direction_id,
            "prohibited_effects": list(self.prohibited_effects),
            "proposal_digest": self.proposal_digest,
            "repository_id": self.repository_id,
            "requested_effects": list(self.requested_effects),
            "schema_version": 1,
            "task": self.task,
        }


@dataclass(frozen=True, slots=True)
class ConversationHandoffDraft:
    """Durable approved task that is ready only for later preflight preparation."""

    approved_direction: ApprovedDirectionVersion
    proposal_digest: str
    authority: HandoffAuthority
    run_intent: RunIntent
    status: str = "ready-for-preflight"
    summary: str = "Task approved and stored. No run has started."
    next_action: str = "Prepare the final run preview."
    execution_authorized: bool = False

    def to_json(self) -> JsonObject:
        return {
            "approved_direction": self.approved_direction.to_json(),
            "authority": self.authority.to_json(),
            "execution_authorized": self.execution_authorized,
            "next_action": self.next_action,
            "proposal_digest": self.proposal_digest,
            "run_intent": self.run_intent.to_json(),
            "schema_version": 1,
            "status": self.status,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class ConversationHandoffStatus:
    """Read-only ordinary-language status for one exact conversation proposal."""

    proposal_digest: str
    direction_id: str
    review: ConversationReview
    status: str
    summary: str
    next_action: str
    execution_authorized: bool = False

    def to_json(self) -> JsonObject:
        return {
            "direction_id": self.direction_id,
            "execution_authorized": self.execution_authorized,
            "next_action": self.next_action,
            "proposal_digest": self.proposal_digest,
            "review": self.review.to_json(),
            "schema_version": 1,
            "status": self.status,
            "summary": self.summary,
        }


class ConversationConflictError(RuntimeError):
    """A handoff no longer matches its exact proposal or durable authority."""


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


def _task_output_from_json(value: object) -> ConversationTask:
    data = _object(value, "conversation proposal task")
    if set(data) != _TASK_OUTPUT_KEYS:
        raise ValidationError("conversation proposal task fields do not match schema version 1")
    _schema_one(data["schema_version"], "conversation proposal task")
    return ConversationTask(
        handoff_id=_identifier(data["handoff_id"], "conversation proposal handoff_id"),
        repository_id=_identifier(data["repository_id"], "conversation proposal repository_id"),
        task=_text(data["task"], "conversation proposal task"),
        assumptions=_texts(
            data["assumptions"], "conversation proposal assumptions", required=False
        ),
        allowed_effects=_texts(
            data["allowed_effects"],
            "conversation proposal allowed_effects",
            required=True,
        ),
        prohibited_effects=_texts(
            data["prohibited_effects"],
            "conversation proposal prohibited_effects",
            required=False,
        ),
        acceptance=_texts(data["acceptance"], "conversation proposal acceptance", required=True),
    )


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


def _review_from_json(value: object) -> ConversationReview:
    data = _object(value, "conversation proposal review")
    if set(data) != _REVIEW_KEYS:
        raise ValidationError("conversation proposal review fields do not match schema version 1")
    if data["execution_authorized"] is not False:
        raise ValidationError("conversation proposal review cannot authorize execution")
    return ConversationReview(
        task=_text(data["task"], "conversation proposal review task"),
        assumptions=_texts(
            data["assumptions"], "conversation proposal review assumptions", required=False
        ),
        proposed_effects=_texts(
            data["proposed_effects"],
            "conversation proposal review proposed_effects",
            required=True,
        ),
        prohibited_effects=_texts(
            data["prohibited_effects"],
            "conversation proposal review prohibited_effects",
            required=False,
        ),
        acceptance=_texts(
            data["acceptance"], "conversation proposal review acceptance", required=True
        ),
    )


def _proposal_from_json(value: object) -> ConversationProposal:
    data = _object(value, "conversation proposal")
    if set(data) != _PROPOSAL_KEYS:
        raise ValidationError("conversation proposal fields do not match schema version 1")
    _schema_one(data["schema_version"], "conversation proposal")
    if data["status"] != "awaiting-approval":
        raise ValidationError("conversation proposal status must be awaiting-approval")
    if data["summary"] != _AWAITING_SUMMARY or data["next_action"] != _AWAITING_NEXT_ACTION:
        raise ValidationError(
            "conversation proposal review guidance does not match schema version 1"
        )
    task = _task_output_from_json(data["task"])
    source_binding_digest = _sha256(
        data["source_binding_digest"], "conversation proposal source_binding_digest"
    )
    candidate = parse_direction_candidate(data["direction_candidate"])
    review = _review_from_json(data["review"])
    if review != _review(task):
        raise ValidationError("conversation proposal review disagrees with the exact task")
    if candidate.candidate.id != _direction_id(task):
        raise ValidationError("conversation proposal Direction id disagrees with the exact task")
    if candidate.candidate.text != _render_direction(task):
        raise ValidationError("conversation proposal Direction text disagrees with the exact task")
    expected_change_note = None if candidate.candidate.supersedes is None else _CHANGE_NOTE
    if candidate.candidate.change_note != expected_change_note:
        raise ValidationError("conversation proposal Direction change note is not canonical")
    proposal_digest = _sha256(data["proposal_digest"], "conversation proposal proposal_digest")
    expected_digest = digest_json(
        {
            "direction_candidate": candidate.to_json(),
            "review": review.to_json(),
            "source_binding_digest": source_binding_digest,
            "task": task.to_json(),
        }
    )
    if proposal_digest != expected_digest:
        raise ValidationError("conversation proposal digest does not match its exact content")
    return ConversationProposal(
        task=task,
        source_binding_digest=source_binding_digest,
        direction_candidate=candidate,
        review=review,
        proposal_digest=proposal_digest,
    )


def _approval_action_from_json(value: object) -> ConversationApprovalAction:
    data = _object(value, "conversation approval action")
    if set(data) != _APPROVAL_KEYS:
        raise ValidationError("conversation approval action fields do not match schema version 1")
    _schema_one(data["schema_version"], "conversation approval action")
    if data["decision"] != "approved":
        raise ValidationError("conversation approval action decision must be approved")
    scopes = _texts(
        data["approved_scopes"],
        "conversation approval action approved_scopes",
        required=True,
    )
    if scopes != _APPROVED_SCOPES:
        raise ValidationError("conversation approval action approved_scopes are not exact")
    return ConversationApprovalAction(
        id=_identifier(data["id"], "conversation approval action id"),
        proposal_digest=_sha256(
            data["proposal_digest"], "conversation approval action proposal_digest"
        ),
        candidate_digest=_sha256(
            data["candidate_digest"], "conversation approval action candidate_digest"
        ),
        approved_by=_text(data["approved_by"], "conversation approval action approved_by"),
        approved_at=_text(data["approved_at"], "conversation approval action approved_at"),
        approved_scopes=scopes,
    )


def _authority_records(
    proposal: ConversationProposal,
    action: ConversationApprovalAction,
) -> tuple[DirectionApproval, PromotionGrant]:
    candidate = proposal.direction_candidate
    approval = DirectionApproval(
        id=f"{action.id}.direction",
        direction_id=candidate.candidate.id,
        candidate_digest=candidate.digest,
        approved_by=action.approved_by,
        approved_at=action.approved_at,
        proposal_digest=proposal.proposal_digest,
    )
    basis = candidate.promotion_basis
    grant = PromotionGrant(
        id=f"{action.id}.ledger",
        granted_by=action.approved_by,
        granted_at=action.approved_at,
        candidate_digest=candidate.digest,
        target_head=basis.target_head,
        target_fingerprint=basis.target_fingerprint,
        run_state_sha256=basis.run_state_sha256,
        allowed_paths=(".second-mate/directions.json",),
        allowed_effects=("direction_ledger_write",),
        stop_conditions=("revision_drift", "direction_history_drift", "open_run"),
    )
    return approval, grant


def _receipt(
    kind: str,
    summary: str,
    record: DirectionApproval | PromotionGrant,
) -> AuthorityReceipt:
    return AuthorityReceipt(
        kind=kind,
        status="recorded",
        summary=summary,
        record_id=record.id,
        record=record.to_json(),
    )


def _not_granted(kind: str, summary: str) -> AuthorityReceipt:
    return AuthorityReceipt(
        kind=kind,
        status="not-granted",
        summary=summary,
        record_id=None,
        record=None,
    )


def _handoff_draft(
    proposal: ConversationProposal,
    version: ApprovedDirectionVersion,
) -> ConversationHandoffDraft:
    approval = version.approval
    grant = version.promotion_grant
    authority = HandoffAuthority(
        direction_approval=_receipt(
            "direction-approval",
            "Task meaning approved and recorded.",
            approval,
        ),
        ledger_write_grant=_receipt(
            "direction-ledger-write",
            "One Direction-ledger write approved and recorded.",
            grant,
        ),
        route_approval=_not_granted(
            "route-approval",
            "No execution route has been approved.",
        ),
        execution_consent=_not_granted(
            "execution-consent",
            "No agent run has been authorized.",
        ),
    )
    task = proposal.task
    return ConversationHandoffDraft(
        approved_direction=version,
        proposal_digest=proposal.proposal_digest,
        authority=authority,
        run_intent=RunIntent(
            repository_id=task.repository_id,
            direction_id=version.direction.id,
            direction_digest=version.direction_digest,
            proposal_digest=proposal.proposal_digest,
            task=task.task,
            assumptions=task.assumptions,
            requested_effects=task.allowed_effects,
            prohibited_effects=task.prohibited_effects,
            acceptance=task.acceptance,
        ),
    )


def _expected_version(
    proposal: ConversationProposal,
    approval: DirectionApproval,
    grant: PromotionGrant,
) -> ApprovedDirectionVersion:
    candidate = proposal.direction_candidate.candidate
    direction = Direction(
        id=candidate.id,
        text=candidate.text,
        approval=Approval(
            approved_by=approval.approved_by,
            approved_at=approval.approved_at,
        ),
    )
    return ApprovedDirectionVersion(
        direction=direction,
        direction_digest=digest_json(direction.to_json()),
        approval=approval,
        promotion_grant=grant,
        supersedes=candidate.supersedes,
        change_note=candidate.change_note,
    )


def _version_matches_proposal(
    version: ApprovedDirectionVersion,
    proposal: ConversationProposal,
) -> bool:
    candidate = proposal.direction_candidate.candidate
    return (
        version.direction.id == candidate.id
        and version.direction.text == candidate.text
        and version.approval.candidate_digest == proposal.direction_candidate.digest
        and version.approval.proposal_digest == proposal.proposal_digest
        and version.supersedes == candidate.supersedes
        and version.change_note == candidate.change_note
    )


def _status(
    proposal: ConversationProposal,
    status: str,
) -> ConversationHandoffStatus:
    messages = {
        "awaiting-approval": (
            "Task is awaiting approval. No run has started.",
            _AWAITING_NEXT_ACTION,
        ),
        "ready-for-preflight": (
            "Task approved and stored. Ready for final preflight preparation; no run has started.",
            "Prepare the final run preview.",
        ),
        "conflict": (
            "The repository or stored task no longer matches this proposal. No run has started.",
            "Prepare and review a refreshed task proposal.",
        ),
        "superseded": (
            "This task was superseded by a newer approved Direction. No run has started.",
            "Prepare and review a refreshed task proposal.",
        ),
    }
    summary, next_action = messages[status]
    return ConversationHandoffStatus(
        proposal_digest=proposal.proposal_digest,
        direction_id=proposal.direction_candidate.candidate.id,
        review=proposal.review,
        status=status,
        summary=summary,
        next_action=next_action,
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


def approve_conversation_handoff(
    repository: Path,
    proposal_data: object,
    approval_action_data: object,
) -> ConversationHandoffDraft:
    """Record approved task meaning and one ledger write without authorizing execution."""
    proposal = _proposal_from_json(proposal_data)
    action = _approval_action_from_json(approval_action_data)
    if action.proposal_digest != proposal.proposal_digest:
        raise ValidationError("conversation approval action identifies a different proposal")
    if action.candidate_digest != proposal.direction_candidate.digest:
        raise ValidationError("conversation approval action identifies a different candidate")
    approval, grant = _authority_records(proposal, action)
    expected = _expected_version(proposal, approval, grant)
    try:
        require_direction_promotion_idle(repository)
    except DirectionConflictError as error:
        raise ConversationConflictError(str(error)) from error
    existing = find_direction_version(
        repository,
        proposal.direction_candidate.candidate.id,
    )
    if existing is not None:
        if not existing.is_current:
            if _version_matches_proposal(existing.version, proposal):
                raise ConversationConflictError(
                    "the approved conversation handoff has been superseded"
                )
            raise ConversationConflictError(
                "the conversation handoff id belongs to different stored meaning"
            )
        if existing.version != expected:
            raise ConversationConflictError(
                "the stored conversation handoff does not match this exact approval action"
            )
        return _handoff_draft(proposal, existing.version)
    try:
        version = promote_direction(
            repository,
            proposal.direction_candidate.to_json(),
            approval.to_json(),
            grant.to_json(),
        )
    except DirectionConflictError as error:
        raise ConversationConflictError(str(error)) from error
    return _handoff_draft(proposal, version)


def conversation_handoff_status(
    repository: Path,
    proposal_data: object,
) -> ConversationHandoffStatus:
    """Report proposal readiness without writing or granting any authority."""
    proposal = _proposal_from_json(proposal_data)
    candidate = proposal.direction_candidate
    existing = find_direction_version(repository, candidate.candidate.id)
    if existing is not None:
        if not _version_matches_proposal(existing.version, proposal):
            return _status(proposal, "conflict")
        return _status(
            proposal,
            "ready-for-preflight" if existing.is_current else "superseded",
        )
    try:
        refreshed = prepare_direction(
            repository,
            candidate.candidate.text,
            direction_id=candidate.candidate.id,
            change_note=candidate.candidate.change_note,
        )
    except (DirectionConflictError, ValidationError):
        return _status(proposal, "conflict")
    if refreshed != candidate:
        return _status(proposal, "conflict")
    return _status(proposal, "awaiting-approval")


__all__ = [
    "AuthorityReceipt",
    "ConversationApprovalAction",
    "ConversationConflictError",
    "ConversationHandoffDraft",
    "ConversationHandoffStatus",
    "ConversationProposal",
    "ConversationReview",
    "ConversationTask",
    "HandoffAuthority",
    "RunIntent",
    "approve_conversation_handoff",
    "conversation_handoff_status",
    "prepare_conversation_handoff",
]
