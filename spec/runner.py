"""Run generated tests against generated implementations in isolation."""

from __future__ import annotations

import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RunResult:
    passed: int
    failed: int
    errors: int
    stdout: str
    duration: float
    all_passed: bool
    timeout: bool = False


class TestRunner:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def run(self, impl_code: str, test_code: str, spec_name: str) -> RunResult:
        """Write impl and tests to a temp dir, run pytest, return structured results."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            # Write files
            (tmp_path / f"{spec_name}.py").write_text(impl_code)
            (tmp_path / f"test_{spec_name}.py").write_text(test_code)
            (tmp_path / "conftest.py").write_text("")

            # Run pytest
            start = time.monotonic()
            try:
                proc = subprocess.run(
                    ["python", "-m", "pytest", str(tmp_path), "-v", "--tb=short"],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=tmp,
                )
                duration = time.monotonic() - start
                stdout = proc.stdout + proc.stderr
                return _parse_pytest_output(stdout, duration)

            except subprocess.TimeoutExpired:
                duration = time.monotonic() - start
                return RunResult(
                    passed=0,
                    failed=0,
                    errors=0,
                    stdout=f"Test execution timed out after {self.timeout}s",
                    duration=duration,
                    all_passed=False,
                    timeout=True,
                )


def _parse_pytest_output(stdout: str, duration: float) -> RunResult:
    """Parse pytest -v output to extract pass/fail/error counts."""
    passed = 0
    failed = 0
    errors = 0

    # Look for the summary line: "X passed, Y failed, Z error"
    summary_match = re.search(
        r"(\d+) passed",
        stdout,
    )
    if summary_match:
        passed = int(summary_match.group(1))

    failed_match = re.search(r"(\d+) failed", stdout)
    if failed_match:
        failed = int(failed_match.group(1))

    error_match = re.search(r"(\d+) error", stdout)
    if error_match:
        errors = int(error_match.group(1))

    all_passed = failed == 0 and errors == 0 and passed > 0

    return RunResult(
        passed=passed,
        failed=failed,
        errors=errors,
        stdout=stdout,
        duration=duration,
        all_passed=all_passed,
    )
