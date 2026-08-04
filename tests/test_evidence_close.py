from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest
from test_authority import exact_grant
from test_draft import valid_direction, valid_packet
from test_execution import CountingFixtureExecutor
from test_preflight import (
    enable_fsmonitor_fixture,
    enable_intent_to_add_fixture,
    index_flag_snapshot,
    intent_to_add_snapshot,
    make_repository,
    run_git,
)

import second_mate
from second_mate.store import (
    FileStateStore,
    PosixAtomicWriter,
    StateRecoveryError,
    deterministic_document_bytes,
    deterministic_json_bytes,
    prepare_atomic_write_intent,
)

FS01_RESIDUAL_UNCERTAINTY = (
    "Live provider behavior was not exercised.",
    "Human product review remains outstanding.",
)


def executed_repository(
    tmp_path: Path,
    *,
    fsmonitor: bool = False,
    intent_to_add: bool = False,
) -> Path:
    repository = make_repository(tmp_path)
    if fsmonitor:
        enable_fsmonitor_fixture(repository)
    if intent_to_add:
        enable_intent_to_add_fixture(repository)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    second_mate.start_run(
        draft=draft,
        basis=basis,
        grant_data=exact_grant(draft, basis),
        repository=repository,
        executor=CountingFixtureExecutor(),
        owner_id="owner-1",
    )
    return repository


def fs01_intent_directory(repository: Path) -> Path:
    path = Path(run_git(repository, "rev-parse", "--git-path", "second-mate-fs01-intents"))
    return path if path.is_absolute() else repository / path


def test_state_store_refuses_a_symlinked_parent_before_writing_outside_its_path(
    tmp_path: Path,
) -> None:
    state_directory = tmp_path / "state-directory"
    escaped_state = tmp_path / "escaped-state"
    escaped_state.mkdir()
    state_directory.symlink_to(escaped_state, target_is_directory=True)
    store = FileStateStore(
        state_directory / "state.json",
        intent_directory=tmp_path / "atomic-intents",
    )
    draft = second_mate.create_draft(valid_direction(), valid_packet())

    with pytest.raises(StateRecoveryError, match="symlink"):
        store.save(draft)

    assert list(escaped_state.iterdir()) == []


def test_state_store_refuses_a_symlinked_container_before_creating_state(
    tmp_path: Path,
) -> None:
    escaped_container = tmp_path / "escaped-container"
    escaped_container.mkdir()
    target_alias = tmp_path / "target-alias"
    target_alias.symlink_to(escaped_container, target_is_directory=True)
    store = FileStateStore(
        target_alias / "state-directory" / "state.json",
        intent_directory=tmp_path / "atomic-intents",
    )
    draft = second_mate.create_draft(valid_direction(), valid_packet())

    with pytest.raises(StateRecoveryError, match="target container"):
        store.save(draft)

    assert list(escaped_container.iterdir()) == []
    assert not (tmp_path / "atomic-intents").exists()


def test_state_store_refuses_a_symlinked_intent_directory(tmp_path: Path) -> None:
    state_directory = tmp_path / "state-directory"
    state_directory.mkdir()
    escaped_intents = tmp_path / "escaped-intents"
    escaped_intents.mkdir()
    intent_alias = tmp_path / "atomic-intents"
    intent_alias.symlink_to(escaped_intents, target_is_directory=True)
    store = FileStateStore(
        state_directory / "state.json",
        intent_directory=intent_alias,
    )
    draft = second_mate.create_draft(valid_direction(), valid_packet())

    with pytest.raises(StateRecoveryError, match="intent directory"):
        store.save(draft)

    assert list(escaped_intents.iterdir()) == []
    assert not (state_directory / "state.json").exists()


def test_state_store_refuses_a_symlinked_parent_before_creating_an_intent_directory(
    tmp_path: Path,
) -> None:
    state_directory = tmp_path / "state-directory"
    state_directory.mkdir()
    escaped_parent = tmp_path / "escaped-parent"
    escaped_parent.mkdir()
    intent_parent = tmp_path / "intent-parent"
    intent_parent.symlink_to(escaped_parent, target_is_directory=True)
    store = FileStateStore(
        state_directory / "state.json",
        intent_directory=intent_parent / "atomic-intents",
    )
    draft = second_mate.create_draft(valid_direction(), valid_packet())

    with pytest.raises(StateRecoveryError, match="intent parent directory"):
        store.save(draft)

    assert list(escaped_parent.iterdir()) == []
    assert not (state_directory / "state.json").exists()


@pytest.mark.parametrize("alias_kind", ("symlink", "hardlink"))
@pytest.mark.parametrize("scratch_form", ("legacy", "content-addressed"))
def test_state_store_refuses_an_aliased_atomic_scratch_file_before_external_write(
    tmp_path: Path,
    alias_kind: str,
    scratch_form: str,
) -> None:
    state_directory = tmp_path / "state-directory"
    state_directory.mkdir()
    escaped = tmp_path / "escaped.txt"
    escaped.write_text("outside remains unchanged\n", encoding="utf-8")
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    content = deterministic_document_bytes(draft)
    scratch_name = (
        "state.json.next"
        if scratch_form == "legacy"
        else f"state.json.next.{hashlib.sha256(content).hexdigest()}"
    )
    scratch = state_directory / scratch_name
    if alias_kind == "symlink":
        scratch.symlink_to(escaped)
    else:
        os.link(escaped, scratch)
    store = FileStateStore(
        state_directory / "state.json",
        intent_directory=tmp_path / "atomic-intents",
    )

    with pytest.raises(StateRecoveryError, match="atomic"):
        store.save(draft)

    assert escaped.read_text(encoding="utf-8") == "outside remains unchanged\n"
    assert os.path.samefile(scratch, escaped)


def test_state_store_refuses_an_unproved_exact_content_addressed_collision(
    tmp_path: Path,
) -> None:
    state_directory = tmp_path / "state-directory"
    state_directory.mkdir()
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    content = deterministic_document_bytes(draft)
    scratch = state_directory / f"state.json.next.{hashlib.sha256(content).hexdigest()}"
    scratch.write_bytes(content[: len(content) // 2])
    scratch.chmod(0o600)

    before = scratch.read_bytes()

    with pytest.raises(StateRecoveryError, match="atomic"):
        FileStateStore(
            state_directory / "state.json",
            intent_directory=tmp_path / "atomic-intents",
        ).save(draft)

    assert scratch.read_bytes() == before
    assert not (state_directory / "state.json").exists()


def test_state_store_completes_a_durably_marked_partial_atomic_write(
    tmp_path: Path,
) -> None:
    state_directory = tmp_path / "state-directory"
    state_directory.mkdir()
    intent_directory = tmp_path / "atomic-intents"
    state_path = state_directory / "state.json"
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    content = deterministic_document_bytes(draft)
    intent = prepare_atomic_write_intent(
        state_path,
        content,
        intent_directory=intent_directory,
    )
    assert intent.marker.read_bytes() == content
    intent.scratch.write_bytes(content[: len(content) // 2])
    intent.scratch.chmod(0o600)

    FileStateStore(state_path, intent_directory=intent_directory).save(draft)

    assert state_path.read_bytes() == content
    assert not intent.scratch.exists()
    assert not intent.marker.exists()


def test_state_store_preserves_and_refuses_a_digest_mismatched_canonical_marker(
    tmp_path: Path,
) -> None:
    state_directory = tmp_path / "state-directory"
    state_directory.mkdir()
    intent_directory = tmp_path / "atomic-intents"
    state_path = state_directory / "state.json"
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    content = deterministic_document_bytes(draft)
    interrupted = prepare_atomic_write_intent(
        state_path,
        content,
        intent_directory=intent_directory,
    )
    marker_before = content[: len(content) // 2]
    interrupted.marker.write_bytes(marker_before)
    interrupted.marker.chmod(0o600)

    with pytest.raises(StateRecoveryError, match="declared digest"):
        FileStateStore(state_path, intent_directory=intent_directory).save(draft)

    assert interrupted.marker.read_bytes() == marker_before
    assert not interrupted.scratch.exists()
    assert not state_path.exists()


def test_state_store_ignores_and_preserves_an_unpublished_staging_marker(
    tmp_path: Path,
) -> None:
    state_directory = tmp_path / "state-directory"
    state_directory.mkdir()
    intent_directory = tmp_path / "atomic-intents"
    state_path = state_directory / "state.json"
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    content = deterministic_document_bytes(draft)
    interrupted = prepare_atomic_write_intent(
        state_path,
        content,
        intent_directory=intent_directory,
    )
    staging = interrupted.marker.with_name(
        interrupted.marker.name.replace("intent.", "staging.", 1)
    )
    interrupted.marker.replace(staging)
    before = staging.read_bytes()

    FileStateStore(state_path, intent_directory=intent_directory).save(draft)

    assert state_path.read_bytes() == content
    assert staging.read_bytes() == before


def test_state_store_finishes_an_interrupted_no_replace_marker_publication(
    tmp_path: Path,
) -> None:
    state_directory = tmp_path / "state-directory"
    state_directory.mkdir()
    intent_directory = tmp_path / "atomic-intents"
    state_path = state_directory / "state.json"
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    content = deterministic_document_bytes(draft)
    interrupted = prepare_atomic_write_intent(
        state_path,
        content,
        intent_directory=intent_directory,
    )
    staging = interrupted.marker.with_name(
        interrupted.marker.name.replace("intent.", "staging.", 1)
    )
    os.link(interrupted.marker, staging)
    assert interrupted.marker.stat().st_nlink == 2

    FileStateStore(state_path, intent_directory=intent_directory).save(draft)

    assert state_path.read_bytes() == content
    assert not staging.exists()
    assert not interrupted.marker.exists()


def test_recovered_marker_durability_is_restored_before_scratch_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state-directory"
    state_directory.mkdir()
    intent_directory = tmp_path / "atomic-intents"
    state_path = state_directory / "state.json"
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    content = deterministic_document_bytes(draft)
    intent = prepare_atomic_write_intent(
        state_path,
        content,
        intent_directory=intent_directory,
    )

    def interrupt_durability(candidate: object) -> None:
        assert candidate == intent
        raise StateRecoveryError("simulated marker durability interruption")

    with monkeypatch.context() as context:
        context.setattr("second_mate.store._redurable_atomic_intent", interrupt_durability)
        with pytest.raises(StateRecoveryError, match="durability interruption"):
            FileStateStore(state_path, intent_directory=intent_directory).save(draft)

    assert intent.marker.read_bytes() == content
    assert not intent.scratch.exists()
    assert not state_path.exists()

    FileStateStore(state_path, intent_directory=intent_directory).save(draft)

    assert state_path.read_bytes() == content
    assert not intent.marker.exists()


def test_state_store_preserves_a_digest_mismatched_marker_and_its_scratch(
    tmp_path: Path,
) -> None:
    state_directory = tmp_path / "state-directory"
    state_directory.mkdir()
    intent_directory = tmp_path / "atomic-intents"
    state_path = state_directory / "state.json"
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    content = deterministic_document_bytes(draft)
    interrupted = prepare_atomic_write_intent(
        state_path,
        content,
        intent_directory=intent_directory,
    )
    marker_before = content[: len(content) // 2]
    scratch_before = content[: len(content) // 3]
    interrupted.marker.write_bytes(marker_before)
    interrupted.marker.chmod(0o600)
    interrupted.scratch.write_bytes(scratch_before)
    interrupted.scratch.chmod(0o600)

    with pytest.raises(StateRecoveryError, match="declared digest"):
        FileStateStore(state_path, intent_directory=intent_directory).save(draft)

    assert interrupted.marker.read_bytes() == marker_before
    assert interrupted.scratch.read_bytes() == scratch_before
    assert not state_path.exists()


def test_state_store_preserves_a_post_marker_scratch_collision(tmp_path: Path) -> None:
    state_directory = tmp_path / "state-directory"
    state_directory.mkdir()
    intent_directory = tmp_path / "atomic-intents"
    state_path = state_directory / "state.json"
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    content = deterministic_document_bytes(draft)
    intent = prepare_atomic_write_intent(
        state_path,
        content,
        intent_directory=intent_directory,
    )
    collision = b"same-user target content that is not an interrupted write\n"
    intent.scratch.write_bytes(collision)
    intent.scratch.chmod(0o600)

    with pytest.raises(StateRecoveryError, match="does not match"):
        FileStateStore(state_path, intent_directory=intent_directory).save(draft)

    assert intent.scratch.read_bytes() == collision
    assert intent.marker.is_file()
    assert not state_path.exists()


def test_state_store_refuses_an_unproved_prior_content_addressed_collision(
    tmp_path: Path,
) -> None:
    state_directory = tmp_path / "state-directory"
    state_directory.mkdir()
    foreign_intent = state_directory / f"state.json.next.{'0' * 64}"
    foreign_intent.write_text("different interrupted write\n", encoding="utf-8")
    foreign_intent.chmod(0o600)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    before = foreign_intent.read_bytes()

    with pytest.raises(StateRecoveryError, match="atomic write intent"):
        FileStateStore(
            state_directory / "state.json",
            intent_directory=tmp_path / "atomic-intents",
        ).save(draft)

    assert foreign_intent.read_bytes() == before
    assert not (state_directory / "state.json").exists()


def test_state_store_retires_only_a_durably_marked_prior_atomic_write(
    tmp_path: Path,
) -> None:
    state_directory = tmp_path / "state-directory"
    state_directory.mkdir()
    intent_directory = tmp_path / "atomic-intents"
    state_path = state_directory / "state.json"
    prior_content = b'{"interrupted": true}\n'
    prior = prepare_atomic_write_intent(
        state_path,
        prior_content,
        intent_directory=intent_directory,
    )
    prior.scratch.write_bytes(prior_content[:8])
    prior.scratch.chmod(0o600)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    expected = deterministic_document_bytes(draft)

    FileStateStore(state_path, intent_directory=intent_directory).save(draft)

    assert state_path.read_bytes() == expected
    assert not prior.scratch.exists()
    assert not prior.marker.exists()


def test_state_store_preserves_a_collision_at_a_prior_marked_scratch(
    tmp_path: Path,
) -> None:
    state_directory = tmp_path / "state-directory"
    state_directory.mkdir()
    intent_directory = tmp_path / "atomic-intents"
    state_path = state_directory / "state.json"
    prior = prepare_atomic_write_intent(
        state_path,
        b'{"interrupted": true}\n',
        intent_directory=intent_directory,
    )
    collision = b"same-user content that replaced the prior interrupted write\n"
    prior.scratch.write_bytes(collision)
    prior.scratch.chmod(0o600)
    draft = second_mate.create_draft(valid_direction(), valid_packet())

    with pytest.raises(StateRecoveryError, match="does not match"):
        FileStateStore(state_path, intent_directory=intent_directory).save(draft)

    assert prior.scratch.read_bytes() == collision
    assert prior.marker.is_file()
    assert not state_path.exists()


def test_state_store_refuses_a_malformed_private_scratch_name(tmp_path: Path) -> None:
    state_directory = tmp_path / "state-directory"
    state_directory.mkdir()
    malformed = state_directory / "state.json.next.not-a-content-digest"
    malformed.write_text("not a proved write intent\n", encoding="utf-8")
    malformed.chmod(0o600)
    before = malformed.read_bytes()
    draft = second_mate.create_draft(valid_direction(), valid_packet())

    with pytest.raises(StateRecoveryError, match="atomic write intent"):
        FileStateStore(
            state_directory / "state.json",
            intent_directory=tmp_path / "atomic-intents",
        ).save(draft)

    assert malformed.read_bytes() == before
    assert not (state_directory / "state.json").exists()


def test_first_state_save_fsyncs_the_new_directory_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state-directory"
    calls: list[Path] = []
    monkeypatch.setattr("second_mate.store._fsync_directory", calls.append)
    store = FileStateStore(
        state_directory / "state.json",
        intent_directory=tmp_path / "atomic-intents",
    )

    store.save(second_mate.create_draft(valid_direction(), valid_packet()))

    assert calls == [
        tmp_path,
        tmp_path,
        tmp_path / "atomic-intents",
        tmp_path / "atomic-intents",
        state_directory,
        tmp_path / "atomic-intents",
    ]


def test_existing_state_and_intent_directories_are_redurable_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state_directory = tmp_path / "state-directory"
    state_directory.mkdir()
    intent_directory = tmp_path / "atomic-intents"
    intent_directory.mkdir(mode=0o700)
    calls: list[Path] = []
    monkeypatch.setattr("second_mate.store._fsync_directory", calls.append)
    store = FileStateStore(
        state_directory / "state.json",
        intent_directory=intent_directory,
    )

    store.save(second_mate.create_draft(valid_direction(), valid_packet()))

    assert calls[:2] == [tmp_path, tmp_path]
    assert state_directory in calls
    assert intent_directory in calls


@pytest.mark.parametrize("alias_kind", ("symlink", "hardlink"))
def test_load_state_refuses_an_aliased_durable_state_file(
    tmp_path: Path,
    alias_kind: str,
) -> None:
    repository = executed_repository(tmp_path)
    state_path = repository / ".second-mate" / "state.json"
    external = tmp_path / "external-state.json"
    expected_external = state_path.read_bytes()
    external.write_bytes(expected_external)
    state_path.unlink()
    if alias_kind == "symlink":
        state_path.symlink_to(external)
    else:
        os.link(external, state_path)

    with pytest.raises(StateRecoveryError, match="durable state"):
        second_mate.load_state(repository)

    assert external.read_bytes() == expected_external


def test_evidence_is_claim_fit_and_bound_to_the_exact_after_revision(tmp_path: Path) -> None:
    """Omitting the after probe, sentinel check, or final revision must fail evidence."""
    repository = executed_repository(tmp_path)
    assert hasattr(second_mate, "record_evidence")

    state = second_mate.record_evidence(repository)

    assert state.run.phase == "ready_to_close"
    assert len(state.evidence) == 1
    evidence = state.evidence[0]
    assert evidence["claim"] == "Change the artifact from before to after."
    assert evidence["method"] == "fixture-probe"
    assert evidence["result"] == "pass"
    observation = evidence["observation"]
    assert observation["artifact_value"] == "after\n"
    assert observation["changed_paths"] == ["artifact.txt"]
    assert (
        observation["sentinel_sha256"]
        == hashlib.sha256(b"FIXTURE_SECRET_DO_NOT_COPY\n").hexdigest()
    )
    assert evidence["target_revision"]["fingerprint"] != state.basis.record.revision.fingerprint


@pytest.mark.parametrize("proof_path", ("artifact.txt", "sentinel.txt"))
@pytest.mark.parametrize("alias_kind", ("symlink", "hardlink"))
def test_evidence_refuses_proof_path_aliases_without_reading_through_them(
    tmp_path: Path,
    proof_path: str,
    alias_kind: str,
) -> None:
    """Identical bytes cannot conceal a changed filesystem identity at proof time."""
    repository = executed_repository(tmp_path)
    path = repository / proof_path
    external = tmp_path / f"external-{proof_path}"
    expected_external = path.read_bytes()
    external.write_bytes(expected_external)
    path.unlink()
    if alias_kind == "symlink":
        path.symlink_to(external)
    else:
        os.link(external, path)

    state = second_mate.record_evidence(repository)

    assert state.run.phase == "evidence_failed"
    assert state.evidence[-1]["result"] == "fail"
    observation = state.evidence[-1]["observation"]
    assert any("unalias" in failure for failure in observation["failures"])
    if proof_path == "artifact.txt":
        assert observation["artifact_value"] is None
        assert observation["artifact_sha256"] is None
    else:
        assert observation["sentinel_sha256"] is None
    assert external.read_bytes() == expected_external


@pytest.mark.parametrize("proof_path", ("artifact.txt", "sentinel.txt"))
def test_clean_close_rechecks_hardlink_identity_after_passing_evidence(
    tmp_path: Path,
    proof_path: str,
) -> None:
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    path = repository / proof_path
    external = tmp_path / f"external-{proof_path}"
    external.write_bytes(path.read_bytes())
    path.unlink()
    os.link(external, path)

    with pytest.raises(second_mate.AuthorityError, match="fixture path"):
        second_mate.clean_close(
            repository,
            direction_coverage="still_remaining",
            residual_uncertainty=FS01_RESIDUAL_UNCERTAINTY,
            handoff="Aliased proof paths must not close.",
        )

    state = second_mate.load_state(repository)
    assert state.run.phase == "ready_to_close"
    assert state.closed is False


def test_clean_close_cannot_write_a_copied_state_through_an_unbound_store(
    tmp_path: Path,
) -> None:
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    state_path = repository / ".second-mate" / "state.json"
    before = state_path.read_bytes()
    escaped_path = tmp_path / "escaped" / "state.json"
    escaped_path.parent.mkdir()
    escaped_path.write_bytes(before)
    escaped_before = escaped_path.read_bytes()

    with pytest.raises(second_mate.ValidationError, match="target state path"):
        second_mate.clean_close(
            repository,
            direction_coverage="still_remaining",
            residual_uncertainty=FS01_RESIDUAL_UNCERTAINTY,
            handoff="Close only the target repository's durable state.",
            store=FileStateStore(
                escaped_path,
                intent_directory=tmp_path / "escaped-intents",
            ),
        )

    assert state_path.read_bytes() == before
    assert escaped_path.read_bytes() == escaped_before


def test_clean_close_rejects_a_store_with_an_unbound_intent_directory(
    tmp_path: Path,
) -> None:
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    state_path = repository / ".second-mate" / "state.json"
    before = state_path.read_bytes()

    with pytest.raises(second_mate.ValidationError, match="target intent directory"):
        second_mate.clean_close(
            repository,
            direction_coverage="still_remaining",
            residual_uncertainty=FS01_RESIDUAL_UNCERTAINTY,
            handoff="Bind recovery ownership to this repository.",
            store=FileStateStore(
                state_path,
                intent_directory=tmp_path / "foreign-intents",
            ),
        )

    assert state_path.read_bytes() == before
    assert not (tmp_path / "foreign-intents").exists()


@pytest.mark.parametrize(
    "basis_drift",
    ("branch", "index", "skip-worktree", "fsmonitor-valid", "intent-to-add"),
)
def test_evidence_detects_branch_and_index_only_drift(
    tmp_path: Path,
    basis_drift: str,
) -> None:
    repository = executed_repository(
        tmp_path,
        fsmonitor=basis_drift == "fsmonitor-valid",
        intent_to_add=basis_drift == "intent-to-add",
    )
    if basis_drift == "branch":
        run_git(repository, "switch", "-q", "-c", "same-commit-alternate")
    elif basis_drift == "index":
        artifact = repository / "artifact.txt"
        artifact.write_text("index-only drift\n", encoding="utf-8")
        run_git(repository, "add", "artifact.txt")
        artifact.write_text("after\n", encoding="utf-8")
    elif basis_drift == "fsmonitor-valid":
        before_flags = index_flag_snapshot(repository)
        run_git(repository, "update-index", "--fsmonitor-valid", "sentinel.txt")
        after_flags = index_flag_snapshot(repository)
        assert before_flags[:2] == after_flags[:2]
        assert before_flags[2] == "H sentinel.txt"
        assert after_flags[2] == "h sentinel.txt"
    elif basis_drift == "intent-to-add":
        before_intent = intent_to_add_snapshot(repository)
        run_git(repository, "add", "intent-to-add.txt")
        after_intent = intent_to_add_snapshot(repository)
        assert before_intent[:3] == after_intent[:3]
        assert before_intent[3] == ""
        assert after_intent[3] != ""
    else:
        run_git(repository, "update-index", f"--{basis_drift}", "sentinel.txt")

    state = second_mate.record_evidence(repository)

    assert state.run.phase == "evidence_failed"
    assert state.evidence[-1]["result"] == "fail"
    assert state.evidence[-1]["observation"]["target_revision_matches_authority"] is False


@pytest.mark.parametrize(
    "index_flag",
    ("skip-worktree", "fsmonitor-valid", "intent-to-add"),
)
def test_clean_close_refuses_index_flag_drift_after_passing_evidence(
    tmp_path: Path,
    index_flag: str,
) -> None:
    repository = executed_repository(
        tmp_path,
        fsmonitor=index_flag == "fsmonitor-valid",
        intent_to_add=index_flag == "intent-to-add",
    )
    second_mate.record_evidence(repository)
    if index_flag == "fsmonitor-valid":
        before_flags = index_flag_snapshot(repository)
        run_git(repository, "update-index", "--fsmonitor-valid", "sentinel.txt")
        after_flags = index_flag_snapshot(repository)
        assert before_flags[:2] == after_flags[:2]
        assert before_flags[2] == "H sentinel.txt"
        assert after_flags[2] == "h sentinel.txt"
    elif index_flag == "intent-to-add":
        before_intent = intent_to_add_snapshot(repository)
        run_git(repository, "add", "intent-to-add.txt")
        after_intent = intent_to_add_snapshot(repository)
        assert before_intent[:3] == after_intent[:3]
        assert before_intent[3] == ""
        assert after_intent[3] != ""
    else:
        run_git(repository, "update-index", f"--{index_flag}", "sentinel.txt")

    with pytest.raises(second_mate.AuthorityError, match="revision drift"):
        second_mate.clean_close(
            repository,
            direction_coverage="still_remaining",
            residual_uncertainty=FS01_RESIDUAL_UNCERTAINTY,
            handoff="Index flag drift must block close.",
        )

    assert second_mate.load_state(repository).run.phase == "ready_to_close"


def test_load_state_rejects_a_minimal_forged_passing_evidence_record(tmp_path: Path) -> None:
    """A pass marker plus live fingerprints is not a claim-fit evidence document."""
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    state_path = repository / ".second-mate" / "state.json"
    document = json.loads(state_path.read_bytes())
    original = document["evidence"][-1]
    document["evidence"] = [
        {
            "instruction_fingerprint": original["instruction_fingerprint"],
            "result": "pass",
            "target_revision": original["target_revision"],
        }
    ]
    state_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    before = state_path.read_bytes()

    with pytest.raises(second_mate.ValidationError, match="evidence fields"):
        second_mate.load_state(repository)

    assert state_path.read_bytes() == before


@pytest.mark.parametrize(
    ("field_path", "invalid_value"),
    (
        (("claim",), "A different claim."),
        (("id",), ""),
        (("method",), "invented"),
        (("result",), "uncertain"),
        (("instruction_fingerprint",), ""),
        (("observation", "artifact_path"), "sentinel.txt"),
        (("observation", "artifact_sha256"), "0" * 64),
        (("observation", "artifact_value"), "before\n"),
        (("observation", "changed_paths"), ["sentinel.txt"]),
        (("observation", "failures"), ["forged failure"]),
        (("observation", "instructions_match_preflight"), False),
        (("observation", "sentinel_path"), "artifact.txt"),
        (("observation", "sentinel_sha256"), "0" * 64),
        (("observation", "target_revision_matches_authority"), False),
        (("target_revision", "fingerprint"), "0" * 64),
        (("target_revision", "head"), "wrong-head"),
    ),
)
def test_load_state_rejects_semantically_invalid_passing_evidence(
    tmp_path: Path,
    field_path: tuple[str, ...],
    invalid_value: object,
) -> None:
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    state_path = repository / ".second-mate" / "state.json"
    document = json.loads(state_path.read_bytes())
    owner = document["evidence"][-1]
    for field in field_path[:-1]:
        owner = owner[field]
        assert isinstance(owner, dict)
    owner[field_path[-1]] = invalid_value
    state_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    before = state_path.read_bytes()

    with pytest.raises(second_mate.ValidationError, match="evidence"):
        second_mate.load_state(repository)

    assert state_path.read_bytes() == before


@pytest.mark.parametrize("evidence_result", ("pass", "fail"))
def test_load_state_requires_phase_and_pressure_to_match_latest_evidence(
    tmp_path: Path,
    evidence_result: str,
) -> None:
    repository = executed_repository(tmp_path)
    if evidence_result == "fail":
        (repository / "sentinel.txt").write_text("out-of-boundary drift\n", encoding="utf-8")
    state = second_mate.record_evidence(repository)
    assert state.evidence[-1]["result"] == evidence_result
    state_path = repository / ".second-mate" / "state.json"
    document = json.loads(state_path.read_bytes())
    if evidence_result == "pass":
        document["run"]["phase"] = "evidence_failed"
        document["recovery_pressure"] = "packet"
    else:
        document["run"]["phase"] = "ready_to_close"
        document["recovery_pressure"] = "none"
    state_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    before = state_path.read_bytes()

    with pytest.raises(second_mate.ValidationError, match="latest evidence result"):
        second_mate.load_state(repository)

    assert state_path.read_bytes() == before


@pytest.mark.parametrize(
    "tamper_kind",
    ("failure-list", "match-flag", "safe-sentinel-without-hash"),
)
def test_load_state_rejects_contradictory_failed_evidence_history(
    tmp_path: Path,
    tamper_kind: str,
) -> None:
    repository = executed_repository(tmp_path)
    (repository / "sentinel.txt").write_text("out-of-boundary drift\n", encoding="utf-8")
    state = second_mate.record_evidence(repository)
    assert state.evidence[-1]["result"] == "fail"
    state_path = repository / ".second-mate" / "state.json"
    document = json.loads(state_path.read_bytes())
    observation = document["evidence"][-1]["observation"]
    if tamper_kind == "failure-list":
        observation["failures"] = ["forged but non-empty failure"]
    elif tamper_kind == "match-flag":
        observation["target_revision_matches_authority"] = True
    else:
        observation["sentinel_sha256"] = None
        observation["failures"] = [
            "fixture sentinel is unavailable",
            "target revision is not preflight plus exactly the authorized artifact mutation",
        ]
    state_path.write_bytes(deterministic_json_bytes(document))
    before = state_path.read_bytes()

    with pytest.raises(second_mate.ValidationError, match="evidence"):
        second_mate.load_state(repository)

    assert state_path.read_bytes() == before


def test_failed_evidence_changed_paths_must_match_the_durable_executor_result(
    tmp_path: Path,
) -> None:
    repository = executed_repository(tmp_path)
    (repository / "sentinel.txt").write_text("out-of-boundary drift\n", encoding="utf-8")
    state = second_mate.record_evidence(repository)
    assert state.evidence[-1]["result"] == "fail"
    state_path = repository / ".second-mate" / "state.json"
    document = json.loads(state_path.read_bytes())
    observation = document["evidence"][-1]["observation"]
    observation["changed_paths"] = ["sentinel.txt"]
    revision_failure = (
        "target revision is not preflight plus exactly the authorized artifact mutation"
    )
    insertion = observation["failures"].index(revision_failure)
    observation["failures"].insert(
        insertion,
        "executor result does not identify exactly the granted artifact",
    )
    state_path.write_bytes(deterministic_json_bytes(document))
    before = state_path.read_bytes()

    with pytest.raises(second_mate.ValidationError, match="executor result"):
        second_mate.load_state(repository)

    assert state_path.read_bytes() == before


def test_persisted_evidence_history_cannot_append_after_a_passing_observation(
    tmp_path: Path,
) -> None:
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    state_path = repository / ".second-mate" / "state.json"
    document = json.loads(state_path.read_bytes())
    duplicate = json.loads(json.dumps(document["evidence"][0]))
    duplicate["id"] = f"{document['draft']['packet']['id']}-fixture-evidence-2"
    document["evidence"].append(duplicate)
    state_path.write_bytes(deterministic_json_bytes(document))
    before = state_path.read_bytes()

    with pytest.raises(second_mate.ValidationError, match="after passing evidence"):
        second_mate.load_state(repository)

    assert state_path.read_bytes() == before


@pytest.mark.parametrize("closed_state", (False, True))
def test_load_state_requires_residual_uncertainty_exactly_at_clean_close(
    tmp_path: Path,
    closed_state: bool,
) -> None:
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    if closed_state:
        second_mate.clean_close(
            repository,
            direction_coverage="still_remaining",
            residual_uncertainty=FS01_RESIDUAL_UNCERTAINTY,
            handoff="FS-01 closed with bounded evidence.",
        )
    state_path = repository / ".second-mate" / "state.json"
    document = json.loads(state_path.read_bytes())
    document["residual_uncertainty"] = [] if closed_state else ["Premature uncertainty."]
    state_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    before = state_path.read_bytes()

    with pytest.raises(second_mate.ValidationError, match="residual uncertainty"):
        second_mate.load_state(repository)

    assert state_path.read_bytes() == before


def test_load_state_rejects_duplicate_clean_close_residual_uncertainty(
    tmp_path: Path,
) -> None:
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    second_mate.clean_close(
        repository,
        direction_coverage="still_remaining",
        residual_uncertainty=FS01_RESIDUAL_UNCERTAINTY,
        handoff="FS-01 closed with unique limitations.",
    )
    state_path = repository / ".second-mate" / "state.json"
    document = json.loads(state_path.read_bytes())
    document["residual_uncertainty"].append(FS01_RESIDUAL_UNCERTAINTY[0])
    state_path.write_bytes(deterministic_json_bytes(document))
    before = state_path.read_bytes()

    with pytest.raises(second_mate.ValidationError, match="residual uncertainty"):
        second_mate.load_state(repository)

    assert state_path.read_bytes() == before


def test_durable_state_is_versioned_deterministic_and_excludes_private_material(
    tmp_path: Path,
) -> None:
    """Adding private material or nondeterministic rewrites must fail inspection."""
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    state_path = repository / ".second-mate" / "state.json"
    first = state_path.read_bytes()

    second_mate.record_evidence(repository)
    second = state_path.read_bytes()

    assert second == first
    document = json.loads(second)
    assert document["schema_version"] == 2
    assert second.endswith(b"\n")
    assert b"FIXTURE_SECRET_DO_NOT_COPY" not in second
    assert b"transcript" not in second.lower()
    assert b"credential" not in second.lower()


def test_clean_close_completes_route_without_inflating_direction_proof(tmp_path: Path) -> None:
    """Coupling completed route status to proven Direction coverage must fail close."""
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    assert hasattr(second_mate, "clean_close")

    closed = second_mate.clean_close(
        repository,
        direction_coverage="still_remaining",
        residual_uncertainty=FS01_RESIDUAL_UNCERTAINTY,
        handoff="FS-01 is closed; human review remains before any provider decision.",
    )

    assert closed.closed is True
    assert closed.route_status == "completed"
    assert closed.direction_coverage == "still_remaining"
    assert closed.run.phase == "closed"
    assert len(closed.evidence) == 1
    assert closed.evidence[0]["result"] == "pass"
    assert closed.recovery_pressure == "none"
    assert closed.residual_uncertainty == FS01_RESIDUAL_UNCERTAINTY
    assert closed.handoff == "FS-01 is closed; human review remains before any provider decision."


def test_clean_close_requires_the_known_fs01_residual_uncertainty(tmp_path: Path) -> None:
    """A fixture-only close must retain what its passing evidence did not exercise."""
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)

    with pytest.raises(second_mate.ValidationError, match="residual uncertainty"):
        second_mate.clean_close(
            repository,
            direction_coverage="still_remaining",
            residual_uncertainty=(),
            handoff="FS-01 is closed.",
        )

    state = second_mate.load_state(repository)
    assert state.closed is False
    assert state.route_status == "ready"
    assert state.run.phase == "ready_to_close"


def test_clean_close_rejects_narrative_that_omits_fixed_fs01_limitations(
    tmp_path: Path,
) -> None:
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)

    with pytest.raises(second_mate.ValidationError, match="required FS-01 limitations"):
        second_mate.clean_close(
            repository,
            direction_coverage="still_remaining",
            residual_uncertainty=("None.",),
            handoff="A narrative cannot erase known fixture limitations.",
        )

    assert second_mate.load_state(repository).run.phase == "ready_to_close"


class FailFinalStateWrite:
    def __init__(self) -> None:
        self.delegate = PosixAtomicWriter()

    def write(self, path: Path, content: bytes, *, intent_directory: Path) -> None:
        if path.name == "state.json":
            raise OSError("targeted failure after close journal")
        self.delegate.write(path, content, intent_directory=intent_directory)


def test_clean_close_refuses_an_unproved_journal_scratch_collision(tmp_path: Path) -> None:
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    state_path = repository / ".second-mate" / "state.json"
    before = state_path.read_bytes()
    scratch = state_path.with_name("state.json.pending.next")
    scratch.write_text("unproved target content\n", encoding="utf-8")

    with pytest.raises(second_mate.CloseFailure, match="recoverable"):
        second_mate.clean_close(
            repository,
            direction_coverage="still_remaining",
            residual_uncertainty=FS01_RESIDUAL_UNCERTAINTY,
            handoff="Do not infer scratch ownership from its name.",
        )

    assert state_path.read_bytes() == before
    assert scratch.read_text(encoding="utf-8") == "unproved target content\n"


def test_clean_close_completes_a_partial_content_addressed_journal_write(
    tmp_path: Path,
) -> None:
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    state_path = repository / ".second-mate" / "state.json"
    handoff = "Recover the exact journal scratch and close."
    with pytest.raises(second_mate.CloseFailure):
        second_mate.clean_close(
            repository,
            direction_coverage="still_remaining",
            residual_uncertainty=FS01_RESIDUAL_UNCERTAINTY,
            handoff=handoff,
            store=FileStateStore(
                state_path,
                intent_directory=fs01_intent_directory(repository),
                writer=FailFinalStateWrite(),
            ),
        )
    pending_path = state_path.with_name("state.json.pending")
    journal_content = pending_path.read_bytes()
    intent = prepare_atomic_write_intent(
        pending_path,
        journal_content,
        intent_directory=fs01_intent_directory(repository),
    )
    pending_path.replace(intent.scratch)
    intent.scratch.write_bytes(journal_content[: len(journal_content) // 2])

    closed = second_mate.clean_close(
        repository,
        direction_coverage="still_remaining",
        residual_uncertainty=FS01_RESIDUAL_UNCERTAINTY,
        handoff=handoff,
    )

    assert closed.closed is True
    assert not intent.scratch.exists()
    assert not intent.marker.exists()


def test_load_state_serializes_close_journal_recovery_with_the_run_lock(
    tmp_path: Path,
) -> None:
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    state_path = repository / ".second-mate" / "state.json"
    with pytest.raises(second_mate.CloseFailure):
        second_mate.clean_close(
            repository,
            direction_coverage="still_remaining",
            residual_uncertainty=FS01_RESIDUAL_UNCERTAINTY,
            handoff="Recover this journal before continuation.",
            store=FileStateStore(
                state_path,
                intent_directory=fs01_intent_directory(repository),
                writer=FailFinalStateWrite(),
            ),
        )
    pending_path = state_path.with_name("state.json.pending")
    state_before = state_path.read_bytes()
    pending_before = pending_path.read_bytes()
    git_lock = Path(run_git(repository, "rev-parse", "--git-path", "second-mate-mutation.lock"))
    if not git_lock.is_absolute():
        git_lock = repository / git_lock
    descriptor = os.open(git_lock, os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with pytest.raises(second_mate.RunConflictError, match="lock"):
            second_mate.load_state(repository)
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)

    assert state_path.read_bytes() == state_before
    assert pending_path.read_bytes() == pending_before


def test_close_failure_recovers_from_old_truthful_state_to_whole_final_state(
    tmp_path: Path,
) -> None:
    """Removing the journal must expose a false or partial completed state after this failure."""
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    state_path = repository / ".second-mate" / "state.json"
    before = state_path.read_bytes()
    failing_store = FileStateStore(
        state_path,
        intent_directory=fs01_intent_directory(repository),
        writer=FailFinalStateWrite(),
    )
    assert hasattr(second_mate, "CloseFailure")

    with pytest.raises(second_mate.CloseFailure, match="recoverable"):
        second_mate.clean_close(
            repository,
            direction_coverage="still_remaining",
            residual_uncertainty=FS01_RESIDUAL_UNCERTAINTY,
            handoff="Recover this journal before any continuation.",
            store=failing_store,
        )

    assert state_path.read_bytes() == before
    interrupted = json.loads(before)
    assert interrupted["route_status"] == "ready"
    assert interrupted["closed"] is False
    assert state_path.with_name("state.json.pending").is_file()

    recovered = second_mate.load_state(repository)
    assert recovered.closed is True
    assert recovered.route_status == "completed"
    assert recovered.direction_coverage == "still_remaining"
    assert recovered.evidence[0]["result"] == "pass"
    assert recovered.recovery_pressure == "none"
    assert recovered.handoff == "Recover this journal before any continuation."
    assert not state_path.with_name("state.json.pending").exists()


def test_copied_close_journal_cannot_recover_into_an_identical_clone(
    tmp_path: Path,
) -> None:
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    state_path = repository / ".second-mate" / "state.json"
    with pytest.raises(second_mate.CloseFailure):
        second_mate.clean_close(
            repository,
            direction_coverage="still_remaining",
            residual_uncertainty=FS01_RESIDUAL_UNCERTAINTY,
            handoff="Recover this close only in its original target.",
            store=FileStateStore(
                state_path,
                intent_directory=fs01_intent_directory(repository),
                writer=FailFinalStateWrite(),
            ),
        )
    clone = tmp_path / "clone"
    shutil.copytree(repository, clone)
    clone_state = clone / ".second-mate" / "state.json"
    clone_journal = clone_state.with_name("state.json.pending")
    state_before = clone_state.read_bytes()
    journal_before = clone_journal.read_bytes()

    with pytest.raises(StateRecoveryError, match="target"):
        second_mate.load_state(clone)

    assert clone_state.read_bytes() == state_before
    assert clone_journal.read_bytes() == journal_before


@pytest.mark.parametrize("alias_kind", ("symlink", "hardlink"))
def test_close_recovery_refuses_an_aliased_journal_without_changing_truth(
    tmp_path: Path,
    alias_kind: str,
) -> None:
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    state_path = repository / ".second-mate" / "state.json"
    before = state_path.read_bytes()
    with pytest.raises(second_mate.CloseFailure):
        second_mate.clean_close(
            repository,
            direction_coverage="still_remaining",
            residual_uncertainty=FS01_RESIDUAL_UNCERTAINTY,
            handoff="Recover only an unaliased journal.",
            store=FileStateStore(
                state_path,
                intent_directory=fs01_intent_directory(repository),
                writer=FailFinalStateWrite(),
            ),
        )
    pending_path = state_path.with_name("state.json.pending")
    external = tmp_path / "external-journal.json"
    expected_external = pending_path.read_bytes()
    external.write_bytes(expected_external)
    pending_path.unlink()
    if alias_kind == "symlink":
        pending_path.symlink_to(external)
    else:
        os.link(external, pending_path)

    with pytest.raises(StateRecoveryError, match="close recovery journal"):
        second_mate.load_state(repository)

    assert state_path.read_bytes() == before
    assert external.read_bytes() == expected_external


@pytest.mark.parametrize(
    "tamper_kind",
    ("invalid-final", "illegal-transition", "duplicate-residual"),
)
def test_close_recovery_validates_the_whole_transition_before_replacing_truth(
    tmp_path: Path,
    tamper_kind: str,
) -> None:
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    state_path = repository / ".second-mate" / "state.json"
    before = state_path.read_bytes()
    with pytest.raises(second_mate.CloseFailure):
        second_mate.clean_close(
            repository,
            direction_coverage="still_remaining",
            residual_uncertainty=FS01_RESIDUAL_UNCERTAINTY,
            handoff="Recover only a valid close transition.",
            store=FileStateStore(
                state_path,
                intent_directory=fs01_intent_directory(repository),
                writer=FailFinalStateWrite(),
            ),
        )
    pending_path = state_path.with_name("state.json.pending")
    journal = json.loads(pending_path.read_bytes())
    final_document = journal["final_document"]
    if tamper_kind == "invalid-final":
        final_document["route_status"] = "ready"
    elif tamper_kind == "illegal-transition":
        final_document["run"]["owner_id"] = "forged-owner"
    else:
        final_document["residual_uncertainty"].append(FS01_RESIDUAL_UNCERTAINTY[0])
    journal["final_sha256"] = hashlib.sha256(deterministic_json_bytes(final_document)).hexdigest()
    pending_path.write_bytes(deterministic_json_bytes(journal))
    pending_before = pending_path.read_bytes()

    with pytest.raises(StateRecoveryError, match="transition"):
        second_mate.load_state(repository)

    assert state_path.read_bytes() == before
    assert pending_path.read_bytes() == pending_before


def test_close_recovery_rejects_contradictory_duplicate_journal_fields(
    tmp_path: Path,
) -> None:
    """Last-key-wins decoding must not authorize an ambiguous recovery journal."""
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    state_path = repository / ".second-mate" / "state.json"
    before = state_path.read_bytes()
    with pytest.raises(second_mate.CloseFailure):
        second_mate.clean_close(
            repository,
            direction_coverage="still_remaining",
            residual_uncertainty=FS01_RESIDUAL_UNCERTAINTY,
            handoff="Recover this journal before any continuation.",
            store=FileStateStore(
                state_path,
                intent_directory=fs01_intent_directory(repository),
                writer=FailFinalStateWrite(),
            ),
        )
    pending_path = state_path.with_name("state.json.pending")
    document = pending_path.read_text(encoding="utf-8")
    marker = '  "schema_version": 2\n}\n'
    assert document.endswith(marker)
    ambiguous = document.removesuffix(marker) + '  "schema_version": 999,\n' + marker
    pending_path.write_text(ambiguous, encoding="utf-8")

    with pytest.raises(StateRecoveryError, match=r"duplicate.*schema_version"):
        second_mate.load_state(repository)

    assert state_path.read_bytes() == before
    assert pending_path.read_text(encoding="utf-8") == ambiguous
    assert json.loads(ambiguous)["schema_version"] == 2


@pytest.mark.parametrize("invalid_version", (True, 1.0, 1))
def test_close_recovery_requires_a_literal_integer_journal_schema_version(
    tmp_path: Path,
    invalid_version: object,
) -> None:
    repository = executed_repository(tmp_path)
    second_mate.record_evidence(repository)
    state_path = repository / ".second-mate" / "state.json"
    before = state_path.read_bytes()
    with pytest.raises(second_mate.CloseFailure):
        second_mate.clean_close(
            repository,
            direction_coverage="still_remaining",
            residual_uncertainty=FS01_RESIDUAL_UNCERTAINTY,
            handoff="Recover this journal before any continuation.",
            store=FileStateStore(
                state_path,
                intent_directory=fs01_intent_directory(repository),
                writer=FailFinalStateWrite(),
            ),
        )
    pending_path = state_path.with_name("state.json.pending")
    journal = json.loads(pending_path.read_bytes())
    journal["schema_version"] = invalid_version
    pending_path.write_text(
        json.dumps(journal, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    pending_bytes = pending_path.read_bytes()

    with pytest.raises(StateRecoveryError, match="journal schema"):
        second_mate.load_state(repository)

    assert state_path.read_bytes() == before
    assert pending_path.read_bytes() == pending_bytes


def test_failed_evidence_retries_after_bounded_repair_without_redispatch(tmp_path: Path) -> None:
    """Blocking a repaired re-probe or invoking the executor again must fail recovery."""
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    basis = second_mate.preflight(draft, repository)
    executor = CountingFixtureExecutor()
    second_mate.start_run(
        draft=draft,
        basis=basis,
        grant_data=exact_grant(draft, basis),
        repository=repository,
        executor=executor,
        owner_id="owner-1",
    )
    sentinel_path = repository / "sentinel.txt"
    sentinel_before = sentinel_path.read_bytes()
    sentinel_path.write_text("temporary out-of-boundary drift\n", encoding="utf-8")

    failed = second_mate.record_evidence(repository)

    assert executor.invocation_count == 1
    assert failed.closed is False
    assert failed.route_status == "ready"
    assert failed.run.phase == "evidence_failed"
    assert failed.recovery_pressure == "packet"
    assert [item["result"] for item in failed.evidence] == ["fail"]
    sentinel_path.write_bytes(sentinel_before)

    repaired = second_mate.record_evidence(repository)

    assert executor.invocation_count == 1
    assert repaired.closed is False
    assert repaired.route_status == "ready"
    assert repaired.run.phase == "ready_to_close"
    assert repaired.recovery_pressure == "none"
    assert [item["result"] for item in repaired.evidence] == ["fail", "pass"]
    closed = second_mate.clean_close(
        repository,
        direction_coverage="still_remaining",
        residual_uncertainty=(
            *FS01_RESIDUAL_UNCERTAINTY,
            "The repaired evidence failure remains recorded.",
        ),
        handoff="Bounded evidence recovery completed without redispatch.",
    )
    assert closed.closed is True
    assert closed.route_status == "completed"
    assert [item["result"] for item in closed.evidence] == ["fail", "pass"]
