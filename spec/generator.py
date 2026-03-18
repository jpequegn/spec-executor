"""Generate Python implementations from SpecDocument using Claude."""

from __future__ import annotations

import ast
import re

import anthropic

from spec.feedback import Feedback
from spec.parser import SpecDocument

SYSTEM_PROMPT = """\
You are an implementation generator. Given a function specification, generate a complete Python implementation.

Rules:
- Implement EXACTLY the function described in the signature
- Follow ALL behavior bullets precisely
- Use only the Python standard library (no external packages)
- Include necessary imports at the top of the file
- Do not include any tests, examples, or explanation
- Do not wrap the code in markdown fences
- Output ONLY the Python code
"""

RETRY_ADDENDUM = """\

You are retrying a failed implementation. Below is your previous code and the test failures it produced.
Fix the issues while still following all the rules above. Pay close attention to the error messages.
"""


class ImplGenerationError(Exception):
    """Raised when implementation generation fails."""


def _build_spec_context(spec: SpecDocument) -> str:
    behavior_list = "\n".join(f"- {b}" for b in spec.behavior)
    examples_block = "\n\n".join(spec.examples) if spec.examples else "(none)"

    return f"""\
## Function name
{spec.name}

## Description
{spec.description}

## Signature
```python
{spec.signature}
```

## Behavior
{behavior_list}

## Examples
```python
{examples_block}
```
"""


def _build_user_prompt(spec: SpecDocument, attempt: int, feedback: Feedback | None) -> str:
    parts = [f"Generate a Python implementation for the following function (attempt {attempt}).\n"]
    parts.append(_build_spec_context(spec))

    if feedback is not None:
        parts.append("## Previous implementation\n```python\n" + feedback.previous_code + "\n```\n")
        parts.append("## Failing tests\n" + "\n".join(f"- {t}" for t in feedback.failing_test_names) + "\n")
        parts.append("## Error output\n```\n" + feedback.error_output + "\n```\n")
        parts.append("Fix these failures. Output ONLY the corrected Python code.\n")

    return "\n".join(parts)


class ImplGenerator:
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic()
        self.model = model

    def generate(self, spec: SpecDocument, attempt: int = 1, feedback: Feedback | None = None) -> str:
        """Generate a Python implementation from a SpecDocument.

        On retry (attempt > 1), includes previous code and test failure feedback.
        Returns syntactically valid Python source code.
        """
        system = SYSTEM_PROMPT
        if feedback is not None:
            system += RETRY_ADDENDUM

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": _build_user_prompt(spec, attempt, feedback)}],
        )

        code = response.content[0].text
        code = _strip_markdown_fences(code)
        _validate_syntax(code)
        return code


def _strip_markdown_fences(code: str) -> str:
    """Strip markdown code fences if Claude wrapped the output."""
    code = code.strip()
    m = re.match(r"^```\w*\n(.*?)```$", code, re.DOTALL)
    if m:
        return m.group(1).strip()
    return code


def _validate_syntax(code: str) -> None:
    """Validate that the generated code is syntactically valid Python."""
    try:
        ast.parse(code)
    except SyntaxError as e:
        raise ImplGenerationError(f"Generated code has syntax error: {e}") from e
