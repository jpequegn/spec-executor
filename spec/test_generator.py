"""Generate pytest test files from SpecDocument using Claude."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import anthropic

from spec.parser import SpecDocument

SYSTEM_PROMPT = """\
You are a test generator. Given a function specification, generate a complete pytest test file.

Rules:
- Use ONLY pytest and unittest.mock (no external mocking libraries)
- Import the function as: from {module_name} import {function_name}
- Generate exactly one test function per test name provided
- Use spec examples as inline assertions where possible
- Include type annotations on test functions (-> None)
- Do not include any explanation, only output the Python code
- Do not wrap the code in markdown fences
"""


def _build_user_prompt(spec: SpecDocument) -> str:
    behavior_list = "\n".join(f"- {b}" for b in spec.behavior)
    examples_block = "\n\n".join(spec.examples) if spec.examples else "(none)"
    test_names_list = "\n".join(f"- {t}" for t in spec.test_names)

    return f"""\
Generate a pytest test file for the following function.

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

## Test functions to generate (use exactly these names)
{test_names_list}

Import the function as: from {spec.name} import {spec.name}
"""


class TestGenerationError(Exception):
    """Raised when test generation fails."""


class TestGenerator:
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic()
        self.model = model

    def generate(self, spec: SpecDocument) -> str:
        """Generate a pytest test file from a SpecDocument.

        Returns the generated Python source code as a string.
        Validates that all test names are present and the code is syntactically valid.
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT.format(
                module_name=spec.name,
                function_name=spec.name,
            ),
            messages=[{"role": "user", "content": _build_user_prompt(spec)}],
        )

        code = response.content[0].text
        code = _strip_markdown_fences(code)
        _validate_generated_tests(code, spec)
        return code

    def generate_and_save(self, spec: SpecDocument, output_dir: str | Path = "tests_generated") -> Path:
        """Generate tests and save to tests_generated/test_{name}.py."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        code = self.generate(spec)
        output_path = output_dir / f"test_{spec.name}.py"
        output_path.write_text(code)
        return output_path


def _strip_markdown_fences(code: str) -> str:
    """Strip markdown code fences if Claude wrapped the output."""
    code = code.strip()
    m = re.match(r"^```\w*\n(.*?)```$", code, re.DOTALL)
    if m:
        return m.group(1).strip()
    return code


def _validate_generated_tests(code: str, spec: SpecDocument) -> None:
    """Validate that the generated code is syntactically valid and contains all test functions."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise TestGenerationError(f"Generated code has syntax error: {e}") from e

    function_names = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }

    missing = set(spec.test_names) - function_names
    if missing:
        raise TestGenerationError(
            f"Generated code missing test functions: {', '.join(sorted(missing))}"
        )
