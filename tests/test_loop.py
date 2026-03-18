"""Tests for the iteration loop."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from spec.feedback import Feedback, FeedbackParser, FailingTest
from spec.generator import ImplGenerator
from spec.loop import GenerationLoop, LoopResult
from spec.parser import SpecDocument, parse_spec
from spec.runner import RunResult, TestRunner
from spec.test_generator import TestGenerator

SPECS_DIR = Path(__file__).parent.parent / "specs"

GOOD_IMPL = "def retry_with_backoff(): pass  # good"
BAD_IMPL = "def retry_with_backoff(): pass  # bad"
TEST_CODE = "def test_succeeds_on_final_attempt(): pass"


@pytest.fixture()
def spec() -> SpecDocument:
    return parse_spec(SPECS_DIR / "retry_with_backoff.md")


def _make_passing_result() -> RunResult:
    return RunResult(passed=5, failed=0, errors=0, stdout="5 passed", duration=0.5, all_passed=True)


def _make_failing_result(passed: int = 3, failed: int = 2) -> RunResult:
    return RunResult(
        passed=passed,
        failed=failed,
        errors=0,
        stdout="test_foo FAILED\ntest_bar FAILED\n3 passed, 2 failed",
        duration=0.5,
        all_passed=False,
    )


def _make_feedback(attempt: int) -> Feedback:
    return Feedback(
        attempt=attempt,
        failing_tests=[FailingTest(name="test_foo", assertion_error="assert False", context_lines="")],
        passing_tests=["test_bar"],
        summary=f"1/2 passing on attempt {attempt}",
        previous_code=BAD_IMPL,
    )


class TestGenerationLoopSuccess:
    def test_succeeds_on_first_attempt(self, spec: SpecDocument, tmp_path: Path):
        test_gen = MagicMock(spec=TestGenerator)
        test_gen.generate.return_value = TEST_CODE

        impl_gen = MagicMock(spec=ImplGenerator)
        impl_gen.generate.return_value = GOOD_IMPL

        runner = MagicMock(spec=TestRunner)
        runner.run.return_value = _make_passing_result()

        loop = GenerationLoop(
            impl_generator=impl_gen,
            test_generator=test_gen,
            runner=runner,
            output_dir=tmp_path,
        )
        result = loop.run(spec, max_attempts=3)

        assert result.success is True
        assert result.attempts == 1
        assert result.final_impl == GOOD_IMPL
        assert (tmp_path / "retry_with_backoff.py").exists()

    def test_succeeds_on_second_attempt(self, spec: SpecDocument, tmp_path: Path):
        test_gen = MagicMock(spec=TestGenerator)
        test_gen.generate.return_value = TEST_CODE

        impl_gen = MagicMock(spec=ImplGenerator)
        impl_gen.generate.side_effect = [BAD_IMPL, GOOD_IMPL]

        runner = MagicMock(spec=TestRunner)
        runner.run.side_effect = [_make_failing_result(), _make_passing_result()]

        feedback_parser = MagicMock(spec=FeedbackParser)
        feedback_parser.parse.return_value = _make_feedback(1)

        loop = GenerationLoop(
            impl_generator=impl_gen,
            test_generator=test_gen,
            runner=runner,
            feedback_parser=feedback_parser,
            output_dir=tmp_path,
        )
        result = loop.run(spec, max_attempts=3)

        assert result.success is True
        assert result.attempts == 2
        assert len(result.all_feedback) == 1
        # Second call should have received feedback
        assert impl_gen.generate.call_count == 2
        second_call = impl_gen.generate.call_args_list[1]
        assert second_call.kwargs.get("feedback") is not None or second_call[1].get("feedback") is not None


class TestGenerationLoopFailure:
    def test_exhausts_all_attempts(self, spec: SpecDocument, tmp_path: Path):
        test_gen = MagicMock(spec=TestGenerator)
        test_gen.generate.return_value = TEST_CODE

        impl_gen = MagicMock(spec=ImplGenerator)
        impl_gen.generate.return_value = BAD_IMPL

        runner = MagicMock(spec=TestRunner)
        runner.run.return_value = _make_failing_result()

        feedback_parser = MagicMock(spec=FeedbackParser)
        feedback_parser.parse.side_effect = [_make_feedback(i) for i in range(1, 4)]

        loop = GenerationLoop(
            impl_generator=impl_gen,
            test_generator=test_gen,
            runner=runner,
            feedback_parser=feedback_parser,
            output_dir=tmp_path,
        )
        result = loop.run(spec, max_attempts=3)

        assert result.success is False
        assert result.attempts == 3
        assert len(result.all_feedback) == 3
        assert (tmp_path / "retry_with_backoff.best.py").exists()

    def test_saves_best_attempt(self, spec: SpecDocument, tmp_path: Path):
        test_gen = MagicMock(spec=TestGenerator)
        test_gen.generate.return_value = TEST_CODE

        better_impl = "def retry_with_backoff(): pass  # better"
        impl_gen = MagicMock(spec=ImplGenerator)
        impl_gen.generate.side_effect = [BAD_IMPL, better_impl]

        runner = MagicMock(spec=TestRunner)
        runner.run.side_effect = [
            _make_failing_result(passed=2, failed=3),
            _make_failing_result(passed=4, failed=1),
        ]

        feedback_parser = MagicMock(spec=FeedbackParser)
        feedback_parser.parse.side_effect = [_make_feedback(1), _make_feedback(2)]

        loop = GenerationLoop(
            impl_generator=impl_gen,
            test_generator=test_gen,
            runner=runner,
            feedback_parser=feedback_parser,
            output_dir=tmp_path,
        )
        result = loop.run(spec, max_attempts=2)

        assert result.success is False
        assert result.final_impl == better_impl
        best_file = tmp_path / "retry_with_backoff.best.py"
        assert best_file.read_text() == better_impl


class TestAttemptLogging:
    def test_attempt_logs_recorded(self, spec: SpecDocument, tmp_path: Path):
        test_gen = MagicMock(spec=TestGenerator)
        test_gen.generate.return_value = TEST_CODE

        impl_gen = MagicMock(spec=ImplGenerator)
        impl_gen.generate.return_value = GOOD_IMPL

        runner = MagicMock(spec=TestRunner)
        runner.run.return_value = _make_passing_result()

        loop = GenerationLoop(
            impl_generator=impl_gen,
            test_generator=test_gen,
            runner=runner,
            output_dir=tmp_path,
        )
        result = loop.run(spec)

        assert len(result.all_attempts) == 1
        log = result.all_attempts[0]
        assert log.attempt == 1
        assert log.passed == 5
        assert log.all_passed is True
        assert log.duration > 0
