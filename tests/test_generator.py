"""Tests for the implementation generator."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from spec.generator import Feedback, ImplGenerationError, ImplGenerator, _build_user_prompt, _strip_markdown_fences, _validate_syntax
from spec.parser import SpecDocument, parse_spec

SPECS_DIR = Path(__file__).parent.parent / "specs"

FAKE_IMPL_CODE = '''\
import time
from typing import Callable


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable:
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        raise
                    delay = base_delay * (2 ** attempt)
                    print(f"Retry {attempt + 1}/{max_retries} after {delay}s")
                    time.sleep(delay)
        return wrapper
    return decorator
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
    def test_strips_fences(self):
        assert _strip_markdown_fences("```python\ncode\n```") == "code"

    def test_no_fences(self):
        assert _strip_markdown_fences("code") == "code"


class TestValidateSyntax:
    def test_valid_passes(self):
        _validate_syntax("x = 1")

    def test_invalid_raises(self):
        with pytest.raises(ImplGenerationError, match="syntax error"):
            _validate_syntax("def broken(")


class TestBuildUserPrompt:
    def test_first_attempt_no_feedback(self, spec: SpecDocument):
        prompt = _build_user_prompt(spec, attempt=1, feedback=None)
        assert "attempt 1" in prompt
        assert "retry_with_backoff" in prompt
        assert "Previous implementation" not in prompt

    def test_retry_with_feedback(self, spec: SpecDocument):
        feedback = Feedback(
            failing_tests=["test_foo", "test_bar"],
            error_output="AssertionError: expected 1 got 2",
            previous_code="def retry_with_backoff(): pass",
        )
        prompt = _build_user_prompt(spec, attempt=2, feedback=feedback)
        assert "attempt 2" in prompt
        assert "Previous implementation" in prompt
        assert "test_foo" in prompt
        assert "AssertionError" in prompt
        assert "def retry_with_backoff(): pass" in prompt


class TestImplGenerator:
    @patch("spec.generator.anthropic.Anthropic")
    def test_generate_first_attempt(self, mock_anthropic_cls, spec: SpecDocument):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_mock_response(FAKE_IMPL_CODE)

        generator = ImplGenerator()
        result = generator.generate(spec, attempt=1)

        assert "def retry_with_backoff(" in result
        ast.parse(result)

    @patch("spec.generator.anthropic.Anthropic")
    def test_generate_retry_with_feedback(self, mock_anthropic_cls, spec: SpecDocument):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_mock_response(FAKE_IMPL_CODE)

        feedback = Feedback(
            failing_tests=["test_delay_is_exponential"],
            error_output="assert delays == [0.01, 0.02, 0.04]",
            previous_code="def retry_with_backoff(): pass",
        )

        generator = ImplGenerator()
        result = generator.generate(spec, attempt=2, feedback=feedback)

        assert "def retry_with_backoff(" in result
        # Verify the system prompt included the retry addendum
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "retrying" in call_kwargs["system"].lower()

    @patch("spec.generator.anthropic.Anthropic")
    def test_generate_strips_fences(self, mock_anthropic_cls, spec: SpecDocument):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        fenced = f"```python\n{FAKE_IMPL_CODE}\n```"
        mock_client.messages.create.return_value = _make_mock_response(fenced)

        generator = ImplGenerator()
        result = generator.generate(spec)

        assert not result.startswith("```")
        ast.parse(result)
