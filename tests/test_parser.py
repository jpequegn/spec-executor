"""Tests for the spec parser."""

from pathlib import Path

import pytest

from spec.parser import SpecDocument, SpecParseError, parse_spec


SPECS_DIR = Path(__file__).parent.parent / "specs"


class TestParseRetryWithBackoff:
    """Test parsing the retry_with_backoff spec."""

    @pytest.fixture()
    def doc(self) -> SpecDocument:
        return parse_spec(SPECS_DIR / "retry_with_backoff.md")

    def test_name(self, doc: SpecDocument):
        assert doc.name == "retry_with_backoff"

    def test_description(self, doc: SpecDocument):
        assert "decorator" in doc.description
        assert "retries" in doc.description

    def test_signature(self, doc: SpecDocument):
        assert "def retry_with_backoff(" in doc.signature
        assert "max_retries" in doc.signature

    def test_behavior(self, doc: SpecDocument):
        assert len(doc.behavior) == 5
        assert any("max_retries" in b for b in doc.behavior)

    def test_examples(self, doc: SpecDocument):
        assert len(doc.examples) == 3
        assert any("flaky" in ex for ex in doc.examples)

    def test_test_names(self, doc: SpecDocument):
        expected = [
            "test_succeeds_on_final_attempt",
            "test_raises_after_exhaustion",
            "test_no_retry_on_wrong_exception_type",
            "test_delay_is_exponential",
            "test_no_delay_on_first_success",
        ]
        assert doc.test_names == expected

    def test_raw_markdown(self, doc: SpecDocument):
        assert doc.raw_markdown.startswith("# Spec: retry_with_backoff")


class TestSpecParseErrors:
    """Test error handling for malformed specs."""

    def test_missing_title(self, tmp_path: Path):
        spec = tmp_path / "bad.md"
        spec.write_text("## Description\nSome desc\n## Signature\n```python\ndef f(): ...\n```\n## Behavior\n- does stuff\n## Tests\n- test_x: desc\n")
        with pytest.raises(SpecParseError, match="Missing title"):
            parse_spec(spec)

    def test_missing_required_section(self, tmp_path: Path):
        spec = tmp_path / "bad.md"
        spec.write_text("# Spec: foo\n\n## Description\nSome desc\n")
        with pytest.raises(SpecParseError, match="Missing required sections"):
            parse_spec(spec)

    def test_missing_code_block_in_signature(self, tmp_path: Path):
        spec = tmp_path / "bad.md"
        spec.write_text(
            "# Spec: foo\n\n## Description\nSome desc\n\n## Signature\nno code block here\n\n## Behavior\n- does stuff\n\n## Tests\n- test_x: desc\n"
        )
        with pytest.raises(SpecParseError, match="No code block found in Signature"):
            parse_spec(spec)
