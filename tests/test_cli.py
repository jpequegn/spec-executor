"""Tests for the CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from spec import cli
from spec.loop import AttemptLog, LoopResult


@pytest.fixture()
def runner():
    return CliRunner()


def _make_loop_result(success: bool = True, attempts: int = 1) -> LoopResult:
    return LoopResult(
        success=success,
        attempts=attempts,
        final_impl="def retry_with_backoff(): pass",
        all_attempts=[
            AttemptLog(attempt=1, passed=5, failed=0, errors=0, duration=1.0, all_passed=success)
        ],
    )


class TestCLIHelp:
    def test_main_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Spec Executor" in result.output

    def test_run_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "max-attempts" in result.output

    def test_stats_help(self, runner: CliRunner):
        result = runner.invoke(cli, ["stats", "--help"])
        assert result.exit_code == 0

    def test_version(self, runner: CliRunner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestRunCommand:
    @patch("spec.commands.GenerationLoop")
    def test_run_single_spec(self, mock_loop_cls, runner: CliRunner):
        mock_loop = MagicMock()
        mock_loop_cls.return_value = mock_loop
        mock_loop.run.return_value = _make_loop_result()

        result = runner.invoke(cli, ["run", "specs/retry_with_backoff.md"])
        assert result.exit_code == 0
        mock_loop.run.assert_called_once()

    @patch("spec.commands.GenerationLoop")
    def test_run_directory(self, mock_loop_cls, runner: CliRunner):
        mock_loop = MagicMock()
        mock_loop_cls.return_value = mock_loop
        mock_loop.run.return_value = _make_loop_result()

        result = runner.invoke(cli, ["run", "specs/"])
        assert result.exit_code == 0

    def test_run_nonexistent_path(self, runner: CliRunner):
        result = runner.invoke(cli, ["run", "nonexistent/path"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "Error" in result.output

    @patch("spec.commands.GenerationLoop")
    def test_run_max_attempts_flag(self, mock_loop_cls, runner: CliRunner):
        mock_loop = MagicMock()
        mock_loop_cls.return_value = mock_loop
        mock_loop.run.return_value = _make_loop_result()

        result = runner.invoke(cli, ["run", "specs/retry_with_backoff.md", "-n", "5"])
        assert result.exit_code == 0
        call_kwargs = mock_loop.run.call_args
        assert call_kwargs.kwargs.get("max_attempts") == 5 or call_kwargs[1].get("max_attempts") == 5


class TestStatsCommand:
    def test_stats_no_results(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("spec.commands.RESULTS_FILE", str(tmp_path / "nope.json"))
        result = runner.invoke(cli, ["stats"])
        assert result.exit_code == 0
        assert "No results" in result.output

    def test_stats_with_results(self, runner: CliRunner, tmp_path: Path, monkeypatch):
        results_file = tmp_path / ".results.json"
        results_file.write_text(json.dumps([
            {
                "name": "retry_with_backoff",
                "success": True,
                "attempts": 2,
                "attempt_logs": [
                    {"attempt": 1, "passed": 3, "failed": 2, "errors": 0, "duration": 1.0, "all_passed": False},
                    {"attempt": 2, "passed": 5, "failed": 0, "errors": 0, "duration": 0.8, "all_passed": True},
                ],
            }
        ]))
        monkeypatch.setattr("spec.commands.RESULTS_FILE", str(results_file))

        result = runner.invoke(cli, ["stats"])
        assert result.exit_code == 0
        assert "retry_with_backoff" in result.output
        assert "1/1" in result.output or "PASS" in result.output
