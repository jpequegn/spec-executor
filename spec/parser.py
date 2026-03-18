"""Parse structured spec markdown files into SpecDocument dataclasses."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


class SpecParseError(Exception):
    """Raised when a spec file is missing required sections or is malformed."""

    def __init__(self, message: str, line: int | None = None):
        self.line = line
        prefix = f"line {line}: " if line is not None else ""
        super().__init__(f"{prefix}{message}")


@dataclass
class SpecDocument:
    name: str
    description: str
    signature: str
    behavior: list[str]
    examples: list[str]
    test_names: list[str]
    raw_markdown: str


_REQUIRED_SECTIONS = {"Description", "Signature", "Behavior", "Tests"}


def parse_spec(path: str | Path) -> SpecDocument:
    """Parse a spec markdown file into a SpecDocument.

    Raises SpecParseError if required sections are missing.
    """
    path = Path(path)
    raw = path.read_text()
    return _parse_spec_string(raw)


def _parse_spec_string(raw: str) -> SpecDocument:
    """Parse spec markdown content into a SpecDocument."""
    lines = raw.split("\n")

    # Extract name from title
    name = _extract_name(lines)

    # Split into sections
    sections = _extract_sections(lines)

    # Validate required sections
    missing = _REQUIRED_SECTIONS - set(sections.keys())
    if missing:
        raise SpecParseError(f"Missing required sections: {', '.join(sorted(missing))}")

    description = sections["Description"].strip()
    signature = _extract_code_block(sections["Signature"], "Signature")
    behavior = _extract_bullets(sections["Behavior"])
    examples = _extract_all_code_blocks(sections.get("Examples", ""))
    test_names = _extract_test_names(sections["Tests"])

    return SpecDocument(
        name=name,
        description=description,
        signature=signature,
        behavior=behavior,
        examples=examples,
        test_names=test_names,
        raw_markdown=raw,
    )


def _extract_name(lines: list[str]) -> str:
    """Extract the spec name from the '# Spec: name' title line."""
    for i, line in enumerate(lines):
        m = re.match(r"^#\s+Spec:\s+(.+)$", line.strip())
        if m:
            return m.group(1).strip()
    raise SpecParseError("Missing title line: expected '# Spec: <name>'", line=1)


def _extract_sections(lines: list[str]) -> dict[str, str]:
    """Split markdown into sections keyed by ## header name."""
    sections: dict[str, str] = {}
    current_section: str | None = None
    current_lines: list[str] = []

    for line in lines:
        header_match = re.match(r"^##\s+(.+)$", line.strip())
        if header_match:
            if current_section is not None:
                sections[current_section] = "\n".join(current_lines)
            current_section = header_match.group(1).strip()
            current_lines = []
        elif current_section is not None:
            current_lines.append(line)

    if current_section is not None:
        sections[current_section] = "\n".join(current_lines)

    return sections


def _extract_code_block(text: str, section_name: str) -> str:
    """Extract the content of the first fenced code block."""
    m = re.search(r"```\w*\n(.*?)```", text, re.DOTALL)
    if not m:
        raise SpecParseError(f"No code block found in {section_name} section")
    return m.group(1).strip()


def _extract_all_code_blocks(text: str) -> list[str]:
    """Extract contents of all fenced code blocks."""
    return [m.group(1).strip() for m in re.finditer(r"```\w*\n(.*?)```", text, re.DOTALL)]


def _extract_bullets(text: str) -> list[str]:
    """Extract markdown bullet points."""
    bullets = []
    for line in text.split("\n"):
        m = re.match(r"^\s*[-*]\s+(.+)$", line)
        if m:
            bullets.append(m.group(1).strip())
    return bullets


def _extract_test_names(text: str) -> list[str]:
    """Extract test names from '- test_name: description' bullets."""
    names = []
    for line in text.split("\n"):
        m = re.match(r"^\s*[-*]\s+(test_\w+)", line)
        if m:
            names.append(m.group(1))
    return names
