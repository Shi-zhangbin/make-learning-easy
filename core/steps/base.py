"""
core/steps/base.py — StepHandler base class

Every pipeline step extends StepHandler and provides:
  - execute(): do the work
  - post_gate(): self-check after execution
  - pre_condition(): check before execution
"""
from pathlib import Path
from typing import Optional


class StepResult:
    def __init__(self, success: bool, artifact: Optional[dict] = None,
                 errors: Optional[list[str]] = None):
        self.success = success
        self.artifact = artifact or {}
        self.errors = errors or []

    def __bool__(self):
        return self.success


class StepHandler:
    """Base class for all pipeline step handlers."""

    name: str = ""
    description: str = ""

    def __init__(self, episode_dir: str, design: Optional[dict] = None,
                 tone: Optional[dict] = None):
        self.episode_dir = Path(episode_dir)
        self.design = design or {}
        self.tone = tone or {}

    def pre_condition(self) -> Optional[str]:
        """Check if step can run. Return error string or None."""
        if not self.episode_dir.exists():
            return f"Episode directory does not exist: {self.episode_dir}"
        return None

    def execute(self) -> StepResult:
        """Execute the step. Must be implemented by subclass."""
        raise NotImplementedError

    def post_gate(self, result: StepResult) -> list[str]:
        """Validate step output. Return list of issues (empty = passed)."""
        return []

    def run(self) -> StepResult:
        """Full run: pre_condition → execute → post_gate."""
        # Pre-condition
        err = self.pre_condition()
        if err:
            return StepResult(False, errors=[err])

        # Execute
        result = self.execute()
        if not result:
            return result

        # Post-gate
        issues = self.post_gate(result)
        if issues:
            result.errors.extend(issues)
            return StepResult(False, result.artifact, result.errors)

        return result
