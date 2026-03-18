"""Tests for the test runner."""

from __future__ import annotations

import pytest

from spec.runner import TestRunner

GOOD_IMPL = """\
def add(a, b):
    return a + b
"""

BAD_IMPL = """\
def add(a, b):
    return a - b
"""

SYNTAX_ERROR_IMPL = """\
def add(a, b)
    return a + b
"""

TEST_CODE = """\
from add import add

def test_add_positive():
    assert add(1, 2) == 3

def test_add_negative():
    assert add(-1, -2) == -3

def test_add_zero():
    assert add(0, 0) == 0
"""


class TestTestRunner:
    def test_all_pass(self):
        runner = TestRunner()
        result = runner.run(GOOD_IMPL, TEST_CODE, "add")

        assert result.passed == 3
        assert result.failed == 0
        assert result.errors == 0
        assert result.all_passed is True
        assert result.timeout is False

    def test_partial_failure(self):
        runner = TestRunner()
        result = runner.run(BAD_IMPL, TEST_CODE, "add")

        # add(-1, -2) = -1 - -2 = 1, not -3 → fail
        # add(0, 0) = 0 - 0 = 0 → pass
        # add(1, 2) = 1 - 2 = -1, not 3 → fail
        assert result.passed >= 1
        assert result.failed >= 1
        assert result.all_passed is False

    def test_syntax_error_in_impl(self):
        runner = TestRunner()
        result = runner.run(SYNTAX_ERROR_IMPL, TEST_CODE, "add")

        assert result.all_passed is False
        assert result.errors >= 1

    def test_timeout(self):
        slow_impl = """\
import time
def add(a, b):
    time.sleep(60)
    return a + b
"""
        runner = TestRunner(timeout=2)
        result = runner.run(slow_impl, TEST_CODE, "add")

        assert result.all_passed is False
        assert result.timeout is True
        assert "timed out" in result.stdout

    def test_stdout_captured(self):
        runner = TestRunner()
        result = runner.run(GOOD_IMPL, TEST_CODE, "add")

        assert "test_add_positive" in result.stdout
        assert "passed" in result.stdout

    def test_duration_tracked(self):
        runner = TestRunner()
        result = runner.run(GOOD_IMPL, TEST_CODE, "add")

        assert result.duration > 0
        assert result.duration < 30
