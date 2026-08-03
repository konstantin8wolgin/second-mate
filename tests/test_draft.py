from __future__ import annotations

from typing import Any

import pytest

import second_mate


def valid_direction() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": "D-01",
        "text": "Keep authority explicit.",
        "approval": {
            "approved_by": "fixture-human",
            "approved_at": "2026-08-02T10:00:00Z",
        },
    }


def valid_packet() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": "IP-01",
        "direction_id": "D-01",
        "repository_id": "fs01-fixture",
        "outcome": "Change the artifact from before to after.",
        "route_status": "ready",
        "route": {
            "decision": "direct",
            "direction_id": "D-01",
            "reason": "The isolated fixture is one coherent lifecycle journey.",
        },
        "boundary": {
            "allowed_paths": [".second-mate/state.json", "artifact.txt"],
            "allowed_effects": ["coordinator_state_write", "fixture_file_write"],
            "stop_conditions": ["revision_drift", "boundary_drift"],
        },
        "proof": {
            "kind": "fixture",
            "artifact_path": "artifact.txt",
            "before": "before\n",
            "after": "after\n",
            "sentinel_path": "sentinel.txt",
        },
    }


def test_draft_freezes_approved_direction_and_packet_with_stable_digests() -> None:
    """Changing approved text or the packet after drafting must change its frozen basis."""
    assert hasattr(second_mate, "create_draft")

    draft = second_mate.create_draft(valid_direction(), valid_packet())

    assert (
        draft.direction_digest == "ac632961082f59075e96b678ee72fd572b17448e70bb7f107b48201cc731b170"
    )
    assert draft.packet_digest == "770a152ef585cfcfa3f27cb50124d9436383c5bf8f6b55052e8cca5a816518cb"
    assert draft.packet.direction_id == draft.direction.id
    assert draft.packet.route.decision == "direct"
    assert draft.packet.route.direction_id == draft.direction.id
    assert draft.packet.route_status == "ready"


@pytest.mark.parametrize("document_name", ("direction", "packet"))
@pytest.mark.parametrize("invalid_version", (True, 1.0))
def test_draft_requires_a_literal_integer_schema_version(
    document_name: str, invalid_version: object
) -> None:
    """JSON booleans and floats must not compare equal to schema integer 1."""
    direction = valid_direction()
    packet = valid_packet()
    document = direction if document_name == "direction" else packet
    document["schema_version"] = invalid_version

    with pytest.raises(second_mate.ValidationError, match="integer 1"):
        second_mate.create_draft(direction, packet)


@pytest.mark.parametrize(
    ("proof_field", "unsafe_path"),
    (("artifact_path", ".git/config"), ("sentinel_path", ".git/config")),
)
def test_fs01_rejects_noncanonical_or_git_private_proof_paths(
    proof_field: str,
    unsafe_path: str,
) -> None:
    packet = valid_packet()
    packet["proof"][proof_field] = unsafe_path
    if proof_field == "artifact_path":
        packet["boundary"]["allowed_paths"] = [".second-mate/state.json", unsafe_path]

    with pytest.raises(second_mate.ValidationError, match="proof paths must be exactly"):
        second_mate.create_draft(valid_direction(), packet)
