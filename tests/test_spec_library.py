"""Tests that all spec files in the library parse correctly."""

from __future__ import annotations

from pathlib import Path

import pytest

from spec.parser import SpecDocument, parse_spec

SPECS_DIR = Path(__file__).parent.parent / "specs"

EXPECTED_SPECS = [
    "retry_with_backoff",
    "lru_cache",
    "rate_limiter",
    "circuit_breaker",
    "event_emitter",
    "bounded_queue",
    "debounce",
    "memoize_to_disk",
    "diff_json",
    "topological_sort",
]


class TestSpecLibrary:
    def test_all_specs_exist(self):
        for name in EXPECTED_SPECS:
            path = SPECS_DIR / f"{name}.md"
            assert path.exists(), f"Missing spec: {path}"

    @pytest.mark.parametrize("name", EXPECTED_SPECS)
    def test_spec_parses(self, name: str):
        doc = parse_spec(SPECS_DIR / f"{name}.md")
        assert doc.name == name
        assert doc.description
        assert doc.signature
        assert len(doc.behavior) >= 3
        assert len(doc.test_names) >= 3

    def test_total_spec_count(self):
        specs = [p for p in SPECS_DIR.glob("*.md") if p.name != ".gitkeep"]
        assert len(specs) == 10
