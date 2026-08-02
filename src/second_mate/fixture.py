"""The deterministic FS-01 executor implementation."""

from __future__ import annotations

from second_mate.service import ExecutionRequest, ExecutionResult


class FixtureExecutor:
    """Perform the single safe fixture mutation through the production executor port."""

    name = "fixture"

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        artifact = (request.repository / request.artifact_path).resolve()
        try:
            artifact.relative_to(request.repository.resolve())
        except ValueError as error:
            raise RuntimeError("fixture artifact escapes the target repository") from error
        if request.artifact_path not in request.allowed_paths:
            raise RuntimeError("fixture artifact is outside the granted path boundary")
        try:
            current = artifact.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise RuntimeError("fixture artifact is unavailable as UTF-8 text") from error
        if current != request.expected_before:
            raise RuntimeError("fixture artifact no longer matches the frozen before state")
        artifact.write_text(request.desired_after, encoding="utf-8")
        return ExecutionResult(
            executor_name=self.name,
            changed_paths=(request.artifact_path,),
            observation="fixture artifact changed to the declared after state",
        )
