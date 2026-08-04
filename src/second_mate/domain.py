"""The small, provider-independent FS-01 domain model."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import cast

type JsonScalar = str | int | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]

STATE_PATH = ".second-mate/state.json"


class ValidationError(ValueError):
    """An authority or packet document does not match the frozen FS-01 contract."""


def canonical_json_bytes(value: JsonValue) -> bytes:
    """Return deterministic UTF-8 JSON bytes for hashing and persistence."""
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def digest_json(value: JsonValue) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValidationError(f"{label} must be a JSON object")
    return cast(dict[str, object], value)


def _exact_keys(value: dict[str, object], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ValidationError(f"{label} keys mismatch; missing={missing}, unknown={unknown}")


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be a non-empty string")
    return value


def _version(value: object, label: str) -> int:
    if type(value) is not int or value != 1:
        raise ValidationError(f"{label} must be the integer 1")
    return 1


def _strings(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValidationError(f"{label} must be a list of non-empty strings")
    result = cast(list[str], value)
    if len(result) != len(set(result)):
        raise ValidationError(f"{label} must contain no duplicates")
    return tuple(result)


def _path(value: object, label: str) -> str:
    path = _text(value, label)
    parsed = PurePosixPath(path)
    if parsed.is_absolute() or ".." in parsed.parts or path in {"", "."}:
        raise ValidationError(f"{label} must be a safe repository-relative path")
    return path


@dataclass(frozen=True, slots=True)
class Approval:
    approved_by: str
    approved_at: str

    def to_json(self) -> JsonObject:
        return {"approved_at": self.approved_at, "approved_by": self.approved_by}


@dataclass(frozen=True, slots=True)
class Direction:
    id: str
    text: str
    approval: Approval

    def to_json(self) -> JsonObject:
        return {
            "approval": self.approval.to_json(),
            "id": self.id,
            "schema_version": 1,
            "text": self.text,
        }


@dataclass(frozen=True, slots=True)
class Boundary:
    allowed_paths: tuple[str, ...]
    allowed_effects: tuple[str, ...]
    stop_conditions: tuple[str, ...]

    def to_json(self) -> JsonObject:
        return {
            "allowed_effects": list(self.allowed_effects),
            "allowed_paths": list(self.allowed_paths),
            "stop_conditions": list(self.stop_conditions),
        }


@dataclass(frozen=True, slots=True)
class FixtureProof:
    artifact_path: str
    before: str
    after: str
    sentinel_path: str

    def to_json(self) -> JsonObject:
        return {
            "after": self.after,
            "artifact_path": self.artifact_path,
            "before": self.before,
            "kind": "fixture",
            "sentinel_path": self.sentinel_path,
        }


@dataclass(frozen=True, slots=True)
class RouteDecision:
    decision: str
    direction_id: str
    reason: str

    def to_json(self) -> JsonObject:
        return {
            "decision": self.decision,
            "direction_id": self.direction_id,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class Packet:
    id: str
    direction_id: str
    repository_id: str
    outcome: str
    route_status: str
    route: RouteDecision
    boundary: Boundary
    proof: FixtureProof

    def to_json(self) -> JsonObject:
        return {
            "boundary": self.boundary.to_json(),
            "direction_id": self.direction_id,
            "id": self.id,
            "outcome": self.outcome,
            "proof": self.proof.to_json(),
            "repository_id": self.repository_id,
            "route": self.route.to_json(),
            "route_status": self.route_status,
            "schema_version": 1,
        }


@dataclass(frozen=True, slots=True)
class Draft:
    direction: Direction
    packet: Packet
    direction_digest: str
    packet_digest: str

    def to_json(self) -> JsonObject:
        return {
            "direction": self.direction.to_json(),
            "direction_digest": self.direction_digest,
            "packet": self.packet.to_json(),
            "packet_digest": self.packet_digest,
            "schema_version": 1,
        }


def _parse_direction(value: object) -> Direction:
    data = _object(value, "direction")
    _exact_keys(data, {"schema_version", "id", "text", "approval"}, "direction")
    _version(data["schema_version"], "direction.schema_version")
    approval_data = _object(data["approval"], "direction.approval")
    _exact_keys(approval_data, {"approved_by", "approved_at"}, "direction.approval")
    return Direction(
        id=_text(data["id"], "direction.id"),
        text=_text(data["text"], "direction.text"),
        approval=Approval(
            approved_by=_text(approval_data["approved_by"], "direction.approval.approved_by"),
            approved_at=_text(approval_data["approved_at"], "direction.approval.approved_at"),
        ),
    )


def direction_from_json(value: object) -> Direction:
    """Validate an approved Direction document in the established draft schema."""
    return _parse_direction(value)


def _parse_packet(value: object) -> Packet:
    data = _object(value, "packet")
    _exact_keys(
        data,
        {
            "schema_version",
            "id",
            "direction_id",
            "repository_id",
            "outcome",
            "route",
            "route_status",
            "boundary",
            "proof",
        },
        "packet",
    )
    _version(data["schema_version"], "packet.schema_version")
    if data["route_status"] != "ready":
        raise ValidationError("packet.route_status must be ready")
    route_data = _object(data["route"], "packet.route")
    _exact_keys(route_data, {"decision", "direction_id", "reason"}, "packet.route")
    if route_data["decision"] != "direct":
        raise ValidationError("FS-01 packet.route.decision must be direct")
    route = RouteDecision(
        decision="direct",
        direction_id=_text(route_data["direction_id"], "packet.route.direction_id"),
        reason=_text(route_data["reason"], "packet.route.reason"),
    )

    boundary_data = _object(data["boundary"], "packet.boundary")
    _exact_keys(
        boundary_data,
        {"allowed_paths", "allowed_effects", "stop_conditions"},
        "packet.boundary",
    )
    boundary = Boundary(
        allowed_paths=tuple(
            _path(item, "packet.boundary.allowed_paths item")
            for item in _strings(boundary_data["allowed_paths"], "packet.boundary.allowed_paths")
        ),
        allowed_effects=_strings(
            boundary_data["allowed_effects"], "packet.boundary.allowed_effects"
        ),
        stop_conditions=_strings(
            boundary_data["stop_conditions"], "packet.boundary.stop_conditions"
        ),
    )

    proof_data = _object(data["proof"], "packet.proof")
    _exact_keys(
        proof_data,
        {"kind", "artifact_path", "before", "after", "sentinel_path"},
        "packet.proof",
    )
    if proof_data["kind"] != "fixture":
        raise ValidationError("packet.proof.kind must be fixture")
    proof = FixtureProof(
        artifact_path=_path(proof_data["artifact_path"], "packet.proof.artifact_path"),
        before=_text(proof_data["before"], "packet.proof.before"),
        after=_text(proof_data["after"], "packet.proof.after"),
        sentinel_path=_path(proof_data["sentinel_path"], "packet.proof.sentinel_path"),
    )
    if proof.artifact_path != "artifact.txt" or proof.sentinel_path != "sentinel.txt":
        raise ValidationError("FS-01 proof paths must be exactly artifact.txt and sentinel.txt")

    if set(boundary.allowed_paths) != {STATE_PATH, proof.artifact_path}:
        raise ValidationError(
            "allowed paths must be exactly the coordinator state and fixture artifact"
        )
    if proof.sentinel_path in boundary.allowed_paths:
        raise ValidationError("the sentinel must remain outside the mutation boundary")
    if set(boundary.allowed_effects) != {"coordinator_state_write", "fixture_file_write"}:
        raise ValidationError("FS-01 allows only coordinator state and fixture file writes")
    if not {"boundary_drift", "revision_drift"}.issubset(boundary.stop_conditions):
        raise ValidationError("stop conditions must include boundary_drift and revision_drift")

    direction_id = _text(data["direction_id"], "packet.direction_id")
    if route.direction_id != direction_id:
        raise ValidationError("route decision must interpret the packet Direction version")

    return Packet(
        id=_text(data["id"], "packet.id"),
        direction_id=direction_id,
        repository_id=_text(data["repository_id"], "packet.repository_id"),
        outcome=_text(data["outcome"], "packet.outcome"),
        route_status="ready",
        route=route,
        boundary=boundary,
        proof=proof,
    )


def create_draft(direction_data: object, packet_data: object) -> Draft:
    """Validate and freeze the exact approved Direction and direct packet."""
    direction = _parse_direction(direction_data)
    packet = _parse_packet(packet_data)
    if packet.direction_id != direction.id:
        raise ValidationError("packet direction does not match the approved Direction")
    direction_json = direction.to_json()
    packet_json = packet.to_json()
    return Draft(
        direction=direction,
        packet=packet,
        direction_digest=digest_json(direction_json),
        packet_digest=digest_json(packet_json),
    )


def draft_from_json(value: object) -> Draft:
    """Reconstruct a draft while verifying its stored immutable digests."""
    data = _object(value, "draft")
    _exact_keys(
        data,
        {"schema_version", "direction", "direction_digest", "packet", "packet_digest"},
        "draft",
    )
    _version(data["schema_version"], "draft.schema_version")
    draft = create_draft(data["direction"], data["packet"])
    if _text(data["direction_digest"], "draft.direction_digest") != draft.direction_digest:
        raise ValidationError("stored Direction digest does not match its approved text")
    if _text(data["packet_digest"], "draft.packet_digest") != draft.packet_digest:
        raise ValidationError("stored packet digest does not match its contract")
    return draft
