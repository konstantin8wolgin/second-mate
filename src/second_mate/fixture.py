"""The deterministic FS-01 executor implementation."""

from __future__ import annotations

import os
import stat

from second_mate.service import ExecutionRequest, ExecutionResult


class FixtureExecutor:
    """Perform the single safe fixture mutation through the production executor port."""

    name = "fixture"

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        repository = request.repository.resolve()
        if request.artifact_path not in request.allowed_paths:
            raise RuntimeError("fixture artifact is outside the granted path boundary")
        directory = os.open(repository, os.O_RDONLY | os.O_DIRECTORY)
        descriptor: int | None = None
        try:
            try:
                descriptor = os.open(
                    request.artifact_path,
                    os.O_RDWR | os.O_NOFOLLOW,
                    dir_fd=directory,
                )
                metadata = os.fstat(descriptor)
                entry = os.stat(
                    request.artifact_path,
                    dir_fd=directory,
                    follow_symlinks=False,
                )
                if (
                    not stat.S_ISREG(metadata.st_mode)
                    or metadata.st_nlink != 1
                    or (metadata.st_dev, metadata.st_ino) != (entry.st_dev, entry.st_ino)
                ):
                    raise RuntimeError("fixture artifact must be one unaliased regular file")
                with os.fdopen(descriptor, "r+b", closefd=True) as stream:
                    descriptor = None
                    try:
                        current = stream.read().decode("utf-8")
                    except UnicodeError as error:
                        raise RuntimeError(
                            "fixture artifact is unavailable as UTF-8 text"
                        ) from error
                    if current != request.expected_before:
                        raise RuntimeError(
                            "fixture artifact no longer matches the frozen before state"
                        )
                    stream.seek(0)
                    stream.truncate()
                    stream.write(request.desired_after.encode("utf-8"))
                    stream.flush()
                    os.fsync(stream.fileno())
            except OSError as error:
                raise RuntimeError("fixture artifact cannot be opened safely") from error
        finally:
            if descriptor is not None:
                os.close(descriptor)
            os.close(directory)
        return ExecutionResult(
            executor_name=self.name,
            changed_paths=(request.artifact_path,),
            observation="fixture artifact changed to the declared after state",
        )
