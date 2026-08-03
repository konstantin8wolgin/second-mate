from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest
from test_draft import valid_direction, valid_packet

import second_mate


def run_git(repository: Path, *args: str) -> str:
    environment = {
        **os.environ,
        "GIT_AUTHOR_DATE": "2026-08-02T10:00:00+00:00",
        "GIT_COMMITTER_DATE": "2026-08-02T10:00:00+00:00",
        "GIT_OPTIONAL_LOCKS": "0",
    }
    completed = subprocess.run(
        [
            "git",
            "--no-optional-locks",
            "-c",
            "user.name=FS-01",
            "-c",
            "user.email=fs01@example.invalid",
            *args,
        ],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    return completed.stdout.strip()


def make_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "target"
    repository.mkdir()
    (repository / "AGENTS.md").write_text("Only artifact.txt may change.\n", encoding="utf-8")
    (repository / "artifact.txt").write_text("before\n", encoding="utf-8")
    (repository / "sentinel.txt").write_text("FIXTURE_SECRET_DO_NOT_COPY\n", encoding="utf-8")
    (repository / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "1"\n', encoding="utf-8"
    )
    run_git(repository, "init", "-q")
    run_git(repository, "add", ".")
    run_git(repository, "commit", "-q", "-m", "fixture baseline")
    return repository


def make_repository_with_ignored_instructions(tmp_path: Path) -> Path:
    repository = make_repository(tmp_path)
    (repository / ".gitignore").write_text("AGENTS.md\n", encoding="utf-8")
    run_git(repository, "rm", "--cached", "AGENTS.md")
    run_git(repository, "add", ".gitignore")
    run_git(repository, "commit", "-q", "-m", "keep local instructions ignored")
    return repository


def enable_fsmonitor_fixture(repository: Path) -> None:
    """Enable Git's v2 hook backend so fsmonitor-valid is a persistent index bit."""
    hook = Path(run_git(repository, "rev-parse", "--git-path", "hooks/fsmonitor-test"))
    if not hook.is_absolute():
        hook = repository / hook
    hook.write_text(
        "#!/bin/sh\ntest \"$1\" = 2 || exit 1\nprintf 'fixture-token\\0'\n",
        encoding="utf-8",
    )
    hook.chmod(0o755)
    run_git(repository, "config", "core.fsmonitor", os.fspath(hook))
    run_git(repository, "config", "core.fsmonitorHookVersion", "2")
    run_git(repository, "update-index", "--fsmonitor")
    run_git(repository, "update-index", "--no-fsmonitor-valid", "sentinel.txt")
    assert run_git(repository, "ls-files", "-f", "sentinel.txt") == "H sentinel.txt"


def index_flag_snapshot(repository: Path) -> tuple[str, str, str]:
    return (
        run_git(repository, "ls-files", "--stage", "sentinel.txt"),
        run_git(repository, "ls-files", "-v", "sentinel.txt"),
        run_git(repository, "ls-files", "-f", "sentinel.txt"),
    )


def enable_intent_to_add_fixture(repository: Path) -> None:
    (repository / "intent-to-add.txt").write_bytes(b"")
    run_git(repository, "add", "--intent-to-add", "intent-to-add.txt")


def intent_to_add_snapshot(repository: Path) -> tuple[str, str, str, str]:
    path = "intent-to-add.txt"
    return (
        run_git(repository, "ls-files", "--stage", "--", path),
        run_git(repository, "ls-files", "-v", "--", path),
        run_git(repository, "ls-files", "-f", "--", path),
        run_git(
            repository,
            "diff",
            "--cached",
            "--raw",
            "--no-renames",
            "--ita-invisible-in-index",
            "--",
            path,
        ),
    )


def target_snapshot(repository: Path) -> tuple[str, bytes, int, dict[str, bytes]]:
    index = repository / ".git" / "index"
    files = {
        path.relative_to(repository).as_posix(): path.read_bytes()
        for path in repository.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repository).parts
    }
    return (
        run_git(repository, "status", "--porcelain=v1"),
        index.read_bytes(),
        index.stat().st_mtime_ns,
        files,
    )


def test_preflight_records_exact_read_only_repository_basis(tmp_path: Path) -> None:
    """Any preflight write or omitted target basis must break the consent boundary."""
    repository = make_repository(tmp_path)
    draft = second_mate.create_draft(valid_direction(), valid_packet())
    before = target_snapshot(repository)
    assert hasattr(second_mate, "preflight")

    result = second_mate.preflight(draft, repository)

    assert target_snapshot(repository) == before
    assert not (repository / ".second-mate").exists()
    assert result.record.repository_id == "fs01-fixture"
    assert result.record.target_root == os.fspath(repository.resolve())
    assert result.record.direction_digest == draft.direction_digest
    assert result.record.packet_digest == draft.packet_digest
    assert result.record.revision.head == run_git(repository, "rev-parse", "HEAD")
    assert result.record.revision.branch == run_git(repository, "rev-parse", "--abbrev-ref", "HEAD")
    assert len(result.record.revision.index_sha256) == 64
    assert result.record.affected_baseline.result == "pass"
    assert result.record.affected_baseline.artifact_value == "before\n"
    assert (
        result.record.affected_baseline.sentinel_sha256
        == hashlib.sha256(b"FIXTURE_SECRET_DO_NOT_COPY\n").hexdigest()
    )
    assert [(item.path, item.sha256) for item in result.record.instructions] == [
        (
            "AGENTS.md",
            hashlib.sha256(b"Only artifact.txt may change.\n").hexdigest(),
        )
    ]
    assert [item.path for item in result.record.dependency_state] == ["pyproject.toml"]
    assert result.record.existing_failures == ()
    assert result.record.eligible is True
    assert len(result.digest) == 64


@pytest.mark.parametrize("proof_path", ("artifact.txt", "sentinel.txt"))
def test_preflight_requires_proof_paths_in_the_visible_frozen_revision(
    tmp_path: Path,
    proof_path: str,
) -> None:
    repository = make_repository(tmp_path)
    (repository / ".gitignore").write_text(f"{proof_path}\n", encoding="utf-8")
    run_git(repository, "rm", "--cached", proof_path)
    run_git(repository, "add", ".gitignore")
    run_git(repository, "commit", "-q", "-m", "ignore one proof path")
    draft = second_mate.create_draft(valid_direction(), valid_packet())

    result = second_mate.preflight(draft, repository)

    assert result.record.eligible is False
    assert any("tracked or visible untracked" in item for item in result.record.existing_failures)


@pytest.mark.parametrize("instruction_kind", ("dangling-symlink", "directory"))
def test_preflight_refuses_nonregular_applicable_instruction_entries(
    tmp_path: Path,
    instruction_kind: str,
) -> None:
    repository = make_repository(tmp_path)
    instruction = repository / "AGENTS.md"
    instruction.unlink()
    if instruction_kind == "dangling-symlink":
        instruction.symlink_to("missing-instructions.md")
    else:
        instruction.mkdir()
    draft = second_mate.create_draft(valid_direction(), valid_packet())

    with pytest.raises(second_mate.ValidationError):
        second_mate.preflight(draft, repository)
