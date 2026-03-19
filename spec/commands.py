"""CLI commands for spec-executor."""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from spec.loop import GenerationLoop, LoopResult
from spec.parser import parse_spec, SpecParseError

console = Console()

RESULTS_FILE = "output/.results.json"


def _collect_spec_paths(path: str) -> list[Path]:
    """Resolve a path to a list of spec markdown files."""
    p = Path(path)
    if p.is_file():
        return [p]
    if p.is_dir():
        specs = sorted(p.glob("*.md"))
        specs = [s for s in specs if s.name != ".gitkeep"]
        if not specs:
            raise click.ClickException(f"No .md files found in {p}")
        return specs
    raise click.ClickException(f"Path not found: {p}")


def _save_result(name: str, result: LoopResult) -> None:
    """Append result to the results JSON file for stats tracking."""
    results_path = Path(RESULTS_FILE)
    results_path.parent.mkdir(parents=True, exist_ok=True)

    existing: list[dict] = []
    if results_path.exists():
        try:
            existing = json.loads(results_path.read_text())
        except (json.JSONDecodeError, ValueError):
            existing = []

    entry = {
        "name": name,
        "success": result.success,
        "attempts": result.attempts,
        "attempt_logs": [
            {
                "attempt": a.attempt,
                "passed": a.passed,
                "failed": a.failed,
                "errors": a.errors,
                "duration": a.duration,
                "all_passed": a.all_passed,
            }
            for a in result.all_attempts
        ],
    }

    # Replace existing entry for same spec, or append
    existing = [e for e in existing if e.get("name") != name]
    existing.append(entry)

    results_path.write_text(json.dumps(existing, indent=2))


@click.command()
@click.argument("path", default="specs/")
@click.option("--max-attempts", "-n", default=3, help="Maximum retry attempts per spec.")
@click.option("--verbose", "-v", is_flag=True, help="Show generated code each attempt.")
def run(path: str, max_attempts: int, verbose: bool) -> None:
    """Run spec(s) through the generation loop.

    PATH can be a single .md file or a directory of specs.
    """
    spec_paths = _collect_spec_paths(path)
    loop = GenerationLoop()

    results: list[tuple[str, LoopResult]] = []

    for spec_path in spec_paths:
        try:
            spec = parse_spec(spec_path)
        except SpecParseError as e:
            console.print(f"[red]Error parsing {spec_path}:[/red] {e}")
            continue

        result = loop.run(spec, max_attempts=max_attempts)
        results.append((spec.name, result))
        _save_result(spec.name, result)

    # Print summary table if multiple specs
    if len(results) > 1:
        _print_summary(results)


def _print_summary(results: list[tuple[str, LoopResult]]) -> None:
    """Print a summary table for multi-spec runs."""
    table = Table(title="Results")
    table.add_column("Spec", style="bold")
    table.add_column("Status")
    table.add_column("Attempts", justify="right")
    table.add_column("Final Pass Rate", justify="right")

    for name, result in results:
        status = "[green]PASS[/green]" if result.success else "[red]FAIL[/red]"
        last = result.all_attempts[-1] if result.all_attempts else None
        pass_rate = f"{last.passed}/{last.passed + last.failed + last.errors}" if last else "—"
        table.add_row(name, status, str(result.attempts), pass_rate)

    console.print()
    console.print(table)

    passed = sum(1 for _, r in results if r.success)
    console.print(f"\n[bold]{passed}/{len(results)} specs passing[/bold]")


@click.command()
def stats() -> None:
    """Show pass rate, average attempts, and failures from previous runs."""
    results_path = Path(RESULTS_FILE)
    if not results_path.exists():
        console.print("[dim]No results yet. Run some specs first.[/dim]")
        return

    try:
        data = json.loads(results_path.read_text())
    except (json.JSONDecodeError, ValueError):
        console.print("[red]Corrupted results file.[/red]")
        return

    if not data:
        console.print("[dim]No results yet.[/dim]")
        return

    table = Table(title="Spec Stats")
    table.add_column("Spec", style="bold")
    table.add_column("Status")
    table.add_column("Attempts", justify="right")
    table.add_column("Final Pass Rate", justify="right")
    table.add_column("Duration", justify="right")

    total_success = 0
    total_attempts = 0

    for entry in data:
        name = entry["name"]
        success = entry["success"]
        attempts = entry["attempts"]
        logs = entry.get("attempt_logs", [])
        last = logs[-1] if logs else {}

        status = "[green]PASS[/green]" if success else "[red]FAIL[/red]"
        total_tests = last.get("passed", 0) + last.get("failed", 0) + last.get("errors", 0)
        pass_rate = f"{last.get('passed', 0)}/{total_tests}" if total_tests else "—"
        total_dur = sum(l.get("duration", 0) for l in logs)

        table.add_row(name, status, str(attempts), pass_rate, f"{total_dur:.1f}s")

        if success:
            total_success += 1
        total_attempts += attempts

    console.print(table)

    avg_attempts = total_attempts / len(data) if data else 0
    console.print(f"\n[bold]{total_success}/{len(data)} specs passing[/bold]")
    console.print(f"Average attempts: {avg_attempts:.1f}")
