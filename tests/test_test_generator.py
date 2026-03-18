"""Tests for the test generator."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from spec.parser import SpecDocument, parse_spec
from spec.test_generator import TestGenerationError, TestGenerator, _strip_markdown_fences, _validate_generated_tests

SPECS_DIR = Path(__file__).parent.parent / "specs"

FAKE_GENERATED_CODE = '''\
import time
from unittest.mock import patch as mock_patch

from retry_with_backoff import retry_with_backoff


def test_succeeds_on_final_attempt() -> None:
    attempts = 0

    @retry_with_backoff(max_retries=3, base_delay=0.01)
    def flaky():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ValueError("not yet")
        return "ok"

    assert flaky() == "ok"
    assert attempts == 3


def test_raises_after_exhaustion() -> None:
    @retry_with_backoff(max_retries=2, base_delay=0.01, exceptions=(ValueError,))
    def always_fails():
        raise ValueError("always")

    with pytest.raises(ValueError, match="always"):
        always_fails()


def test_no_retry_on_wrong_exception_type() -> None:
    attempts = 0

    @retry_with_backoff(max_retries=3, base_delay=0.01, exceptions=(ValueError,))
    def wrong_type():
        nonlocal attempts
        attempts += 1
        raise TypeError("wrong")

    with pytest.raises(TypeError):
        wrong_type()
    assert attempts == 1


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
        assert delays == [0.01, 0.02, 0.04]


def test_no_delay_on_first_success() -> None:
    with mock_patch("time.sleep") as mock_sleep:
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def works():
            return "ok"

        assert works() == "ok"
        mock_sleep.assert_not_called()
'''


def _make_mock_response(text: str) -> MagicMock:
    mock_content = MagicMock()
    mock_content.text = text
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    return mock_response


@pytest.fixture()
def spec() -> SpecDocument:
    return parse_spec(SPECS_DIR / "retry_with_backoff.md")


class TestStripMarkdownFences:
    def test_strips_python_fences(self):
        code = "```python\nprint('hello')\n```"
        assert _strip_markdown_fences(code) == "print('hello')"

    def test_no_fences_unchanged(self):
        code = "print('hello')"
        assert _strip_markdown_fences(code) == "print('hello')"


class TestValidateGeneratedTests:
    def test_valid_code_passes(self, spec: SpecDocument):
        _validate_generated_tests(FAKE_GENERATED_CODE, spec)

    def test_syntax_error_raises(self, spec: SpecDocument):
        with pytest.raises(TestGenerationError, match="syntax error"):
            _validate_generated_tests("def broken(", spec)

    def test_missing_test_raises(self, spec: SpecDocument):
        code = "def test_succeeds_on_final_attempt(): pass\n"
        with pytest.raises(TestGenerationError, match="missing test functions"):
            _validate_generated_tests(code, spec)


class TestTestGenerator:
    @patch("spec.test_generator.anthropic.Anthropic")
    def test_generate_returns_valid_code(self, mock_anthropic_cls, spec: SpecDocument):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_mock_response(FAKE_GENERATED_CODE)

        generator = TestGenerator()
        result = generator.generate(spec)

        assert "test_succeeds_on_final_attempt" in result
        assert "test_raises_after_exhaustion" in result
        ast.parse(result)  # valid syntax

    @patch("spec.test_generator.anthropic.Anthropic")
    def test_generate_and_save_creates_file(self, mock_anthropic_cls, spec: SpecDocument, tmp_path: Path):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_mock_response(FAKE_GENERATED_CODE)

        generator = TestGenerator()
        path = generator.generate_and_save(spec, output_dir=tmp_path)

        assert path.exists()
        assert path.name == "test_retry_with_backoff.py"
        ast.parse(path.read_text())

    @patch("spec.test_generator.anthropic.Anthropic")
    def test_generate_strips_markdown_fences(self, mock_anthropic_cls, spec: SpecDocument):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        fenced = f"```python\n{FAKE_GENERATED_CODE}\n```"
        mock_client.messages.create.return_value = _make_mock_response(fenced)

        generator = TestGenerator()
        result = generator.generate(spec)

        assert not result.startswith("```")
        ast.parse(result)
