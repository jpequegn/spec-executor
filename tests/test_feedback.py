"""Tests for the feedback parser."""

from __future__ import annotations

import pytest

from spec.feedback import FeedbackParser

# Real-ish pytest -v --tb=short output with 2 failures and 3 passes
SAMPLE_PYTEST_OUTPUT = """\
============================= test session starts ==============================
platform darwin -- Python 3.12.12, pytest-9.0.2, pluggy-1.6.0 -- /tmp/test/.venv/bin/python3
collected 5 items

test_retry_with_backoff.py::test_succeeds_on_final_attempt PASSED        [ 20%]
test_retry_with_backoff.py::test_raises_after_exhaustion PASSED          [ 40%]
test_retry_with_backoff.py::test_no_retry_on_wrong_exception_type FAILED [ 60%]
test_retry_with_backoff.py::test_delay_is_exponential FAILED             [ 80%]
test_retry_with_backoff.py::test_no_delay_on_first_success PASSED        [100%]

=================================== FAILURES ===================================
_________________________ test_no_retry_on_wrong_exception_type _________________________

    def test_no_retry_on_wrong_exception_type() -> None:
        attempts = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01, exceptions=(ValueError,))
        def wrong_type():
            nonlocal attempts
            attempts += 1
            raise TypeError("wrong")

        with pytest.raises(TypeError):
            wrong_type()
>       assert attempts == 1
E       AssertionError: assert 4 == 1

test_retry_with_backoff.py:42: AssertionError
_________________________ test_delay_is_exponential _________________________

    def test_delay_is_exponential() -> None:
        with mock_patch("time.sleep") as mock_sleep:
            attempts = 0

            @retry_with_backoff(max_retries=3, base_delay=0.01)
            def flaky():
                nonlocal attempts
                attempts += 1
                if attempts <= 3:
                    raise ValueError("fail")
                return "ok"

            flaky()
            delays = [call.args[0] for call in mock_sleep.call_args_list]
>           assert delays == [0.01, 0.02, 0.04]
E           AssertionError: assert [1.0, 2.0, 4.0] == [0.01, 0.02, 0.04]

test_retry_with_backoff.py:60: AssertionError
=========================== short test summary info ============================
FAILED test_retry_with_backoff.py::test_no_retry_on_wrong_exception_type - AssertionError: assert 4 == 1
FAILED test_retry_with_backoff.py::test_delay_is_exponential - AssertionError: assert [1.0, 2.0, 4.0] == [0.01, 0.02, 0.04]
============================= 3 passed, 2 failed in 0.12s =====================
"""

ALL_PASSING_OUTPUT = """\
============================= test session starts ==============================
collected 3 items

test_add.py::test_add_positive PASSED                                    [ 33%]
test_add.py::test_add_negative PASSED                                    [ 66%]
test_add.py::test_add_zero PASSED                                        [100%]

============================== 3 passed in 0.01s ===============================
"""


class TestFeedbackParser:
    def setup_method(self):
        self.parser = FeedbackParser()

    def test_extracts_passing_tests(self):
        fb = self.parser.parse(SAMPLE_PYTEST_OUTPUT, attempt=1)
        assert "test_succeeds_on_final_attempt" in fb.passing_tests
        assert "test_raises_after_exhaustion" in fb.passing_tests
        assert "test_no_delay_on_first_success" in fb.passing_tests
        assert len(fb.passing_tests) == 3

    def test_extracts_failing_test_names(self):
        fb = self.parser.parse(SAMPLE_PYTEST_OUTPUT, attempt=1)
        names = fb.failing_test_names
        assert "test_no_retry_on_wrong_exception_type" in names
        assert "test_delay_is_exponential" in names
        assert len(fb.failing_tests) == 2

    def test_extracts_assertion_errors(self):
        fb = self.parser.parse(SAMPLE_PYTEST_OUTPUT, attempt=1)
        by_name = {t.name: t for t in fb.failing_tests}

        wrong_exc = by_name["test_no_retry_on_wrong_exception_type"]
        assert "assert 4 == 1" in wrong_exc.assertion_error

        delay = by_name["test_delay_is_exponential"]
        assert "[1.0, 2.0, 4.0]" in delay.assertion_error

    def test_summary_format(self):
        fb = self.parser.parse(SAMPLE_PYTEST_OUTPUT, attempt=1)
        assert "3/5" in fb.summary
        assert "test_no_retry_on_wrong_exception_type" in fb.summary
        assert "test_delay_is_exponential" in fb.summary

    def test_attempt_stored(self):
        fb = self.parser.parse(SAMPLE_PYTEST_OUTPUT, attempt=2)
        assert fb.attempt == 2

    def test_previous_code_stored(self):
        fb = self.parser.parse(SAMPLE_PYTEST_OUTPUT, attempt=1, previous_code="code here")
        assert fb.previous_code == "code here"

    def test_all_passing(self):
        fb = self.parser.parse(ALL_PASSING_OUTPUT, attempt=1)
        assert len(fb.passing_tests) == 3
        assert len(fb.failing_tests) == 0
        assert "All tests pass" in fb.summary

    def test_error_output_property(self):
        fb = self.parser.parse(SAMPLE_PYTEST_OUTPUT, attempt=1)
        error = fb.error_output
        assert "test_no_retry_on_wrong_exception_type" in error
        assert "test_delay_is_exponential" in error
