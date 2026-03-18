"""Parse pytest stdout into structured feedback for the implementation generator."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class FailingTest:
    name: str
    assertion_error: str
    context_lines: str


@dataclass
class Feedback:
    """Structured feedback from a test run, used to guide retry attempts."""

    attempt: int
    failing_tests: list[FailingTest] = field(default_factory=list)
    passing_tests: list[str] = field(default_factory=list)
    summary: str = ""
    previous_code: str = ""

    @property
    def failing_test_names(self) -> list[str]:
        return [t.name for t in self.failing_tests]

    @property
    def error_output(self) -> str:
        """Combined error output for all failing tests."""
        parts = []
        for t in self.failing_tests:
            parts.append(f"{t.name}: {t.assertion_error}")
            if t.context_lines:
                parts.append(t.context_lines)
        return "\n".join(parts)


class FeedbackParser:
    """Parse pytest -v --tb=short output into structured Feedback."""

    def parse(self, pytest_stdout: str, attempt: int, previous_code: str = "") -> Feedback:
        passing = self._extract_passing(pytest_stdout)
        failing = self._extract_failing(pytest_stdout)
        total = len(passing) + len(failing)
        summary = self._build_summary(passing, failing, total)

        return Feedback(
            attempt=attempt,
            failing_tests=failing,
            passing_tests=passing,
            summary=summary,
            previous_code=previous_code,
        )

    def _extract_passing(self, stdout: str) -> list[str]:
        """Extract passing test names from 'test_name PASSED' lines."""
        names = []
        for m in re.finditer(r"(test_\w+)\s+PASSED", stdout):
            names.append(m.group(1))
        return names

    def _extract_failing(self, stdout: str) -> list[FailingTest]:
        """Extract failing tests with their assertion errors and context."""
        # Get failing test names from result lines
        failing_names = []
        for m in re.finditer(r"(test_\w+)\s+FAILED", stdout):
            failing_names.append(m.group(1))

        # Parse the short traceback sections for each failure
        failures = []
        for name in failing_names:
            assertion_error = self._extract_assertion_error(stdout, name)
            context_lines = self._extract_context(stdout, name)
            failures.append(FailingTest(
                name=name,
                assertion_error=assertion_error,
                context_lines=context_lines,
            ))

        return failures

    def _extract_assertion_error(self, stdout: str, test_name: str) -> str:
        """Extract the assertion error message for a specific test."""
        context = self._extract_context(stdout, test_name)
        if not context:
            return ""

        # Find E lines (pytest error lines) in the traceback section
        e_lines = []
        for line in context.split("\n"):
            stripped = line.strip()
            if stripped.startswith("E "):
                e_lines.append(stripped[2:].strip())

        return "\n".join(e_lines) if e_lines else ""

    def _extract_context(self, stdout: str, test_name: str) -> str:
        """Extract the surrounding context/traceback for a failing test."""
        # Find the short traceback block for this test
        # Pattern: "_ test_name _" ... until next "_ " or "===="
        pattern = rf"_+ {test_name} _+\n(.*?)(?=\n_+ \w|\n====|\Z)"
        m = re.search(pattern, stdout, re.DOTALL)
        if m:
            return m.group(1).strip()
        return ""

    def _build_summary(self, passing: list[str], failing: list[FailingTest], total: int) -> str:
        n_passing = len(passing)
        if not failing:
            return f"{n_passing}/{total} tests passing. All tests pass!"

        fail_names = ", ".join(f.name for f in failing)
        return f"{n_passing}/{total} tests passing. Failures: {fail_names}"
