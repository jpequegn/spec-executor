"""Orchestrate the generate → test → feedback → retry loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from spec.feedback import Feedback, FeedbackParser
from spec.generator import ImplGenerator
from spec.parser import SpecDocument
from spec.runner import RunResult, TestRunner
from spec.test_generator import TestGenerator

console = Console()


@dataclass
class AttemptLog:
    attempt: int
    passed: int
    failed: int
    errors: int
    duration: float
    all_passed: bool


@dataclass
class LoopResult:
    success: bool
    attempts: int
    final_impl: str
    all_feedback: list[Feedback] = field(default_factory=list)
    all_attempts: list[AttemptLog] = field(default_factory=list)


class GenerationLoop:
    def __init__(
        self,
        impl_generator: ImplGenerator | None = None,
        test_generator: TestGenerator | None = None,
        runner: TestRunner | None = None,
        feedback_parser: FeedbackParser | None = None,
        output_dir: str | Path = "output",
    ):
        self.impl_generator = impl_generator or ImplGenerator()
        self.test_generator = test_generator or TestGenerator()
        self.runner = runner or TestRunner()
        self.feedback_parser = feedback_parser or FeedbackParser()
        self.output_dir = Path(output_dir)

    def run(self, spec: SpecDocument, max_attempts: int = 3) -> LoopResult:
        """Run the full generation loop: generate tests, then iterate on implementation."""
        console.print(Panel(f"[bold]Spec: {spec.name}[/bold]\nMax attempts: {max_attempts}"))

        # Step 1: Generate tests (once, fixed across all attempts)
        console.print("[dim]Generating tests...[/dim]")
        test_code = self.test_generator.generate(spec)
        console.print(f"[green]Tests generated[/green] ({len(spec.test_names)} test functions)")

        # Step 2: Iterate on implementation
        feedback: Feedback | None = None
        all_feedback: list[Feedback] = []
        all_attempts: list[AttemptLog] = []
        best_impl = ""
        best_passed = -1

        for attempt in range(1, max_attempts + 1):
            console.print(f"\n[bold cyan]Attempt {attempt}/{max_attempts}[/bold cyan]")

            # Generate implementation
            console.print("[dim]Generating implementation...[/dim]")
            impl_code = self.impl_generator.generate(spec, attempt=attempt, feedback=feedback)

            # Run tests
            console.print("[dim]Running tests...[/dim]")
            run_result: RunResult = self.runner.run(impl_code, test_code, spec.name)

            attempt_log = AttemptLog(
                attempt=attempt,
                passed=run_result.passed,
                failed=run_result.failed,
                errors=run_result.errors,
                duration=run_result.duration,
                all_passed=run_result.all_passed,
            )
            all_attempts.append(attempt_log)

            console.print(
                f"  {'[green]PASS' if run_result.all_passed else '[red]FAIL'}[/] "
                f"— {run_result.passed} passed, {run_result.failed} failed, "
                f"{run_result.errors} errors ({run_result.duration:.1f}s)"
            )

            # Track best attempt
            if run_result.passed > best_passed:
                best_passed = run_result.passed
                best_impl = impl_code

            if run_result.all_passed:
                self._save_impl(spec.name, impl_code)
                console.print(f"\n[bold green]Success on attempt {attempt}![/bold green]")
                return LoopResult(
                    success=True,
                    attempts=attempt,
                    final_impl=impl_code,
                    all_feedback=all_feedback,
                    all_attempts=all_attempts,
                )

            # Parse feedback for next attempt
            feedback = self.feedback_parser.parse(
                run_result.stdout, attempt=attempt, previous_code=impl_code
            )
            all_feedback.append(feedback)
            console.print(f"  [dim]{feedback.summary}[/dim]")

        # All attempts exhausted — save best
        self._save_best(spec.name, best_impl)
        console.print(f"\n[bold red]Failed after {max_attempts} attempts.[/bold red]")
        console.print(f"Best attempt: {best_passed} tests passing. Saved to output/{spec.name}.best.py")

        return LoopResult(
            success=False,
            attempts=max_attempts,
            final_impl=best_impl,
            all_feedback=all_feedback,
            all_attempts=all_attempts,
        )

    def _save_impl(self, name: str, code: str) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / f"{name}.py").write_text(code)

    def _save_best(self, name: str, code: str) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / f"{name}.best.py").write_text(code)
