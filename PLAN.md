# Spec Executor — Implementation Plan

## What We're Building

A tool that takes a spec written in structured markdown, generates an implementation via Claude, runs the tests, reads the failure output, and iterates until the tests pass — or it gives up after N attempts with a diagnostic.

The developer writes the spec. The agent executes it. **Spec quality becomes the engineering skill.**

## Why This Matters

Three converging signals this week: Amazon's Kiro IDE (spec-driven development), Boris Cherny's Claude Code episode (humans write intent, agents write code), OpenClaw pattern (agents that self-correct from test output). The paradigm shift is: code is becoming a build artifact, not source of truth. The spec is the source of truth.

## The Spec Format

A spec is a markdown file with structured sections:

```markdown
# Spec: retry_with_backoff

## Description
A function decorator that retries the wrapped function on exception,
with exponential backoff between attempts.

## Signature
```python
def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple = (Exception,)
) -> Callable
```

## Behavior
- Retries up to `max_retries` times on any exception in `exceptions`
- Waits `base_delay * 2^attempt` seconds between attempts (attempt starts at 0)
- On final failure, raises the original exception unchanged
- Does NOT retry if exception type not in `exceptions`
- Logs each retry attempt with attempt number and delay

## Examples
```python
# Succeeds on 3rd attempt
attempts = 0
@retry_with_backoff(max_retries=3, base_delay=0.01)
def flaky():
    global attempts
    attempts += 1
    if attempts < 3:
        raise ValueError("not yet")
    return "ok"

assert flaky() == "ok"
assert attempts == 3
```

## Tests
- test_succeeds_on_final_attempt: passes after max_retries attempts
- test_raises_after_exhaustion: raises original exception when all retries fail
- test_no_retry_on_wrong_exception: does not retry TypeError if only ValueError specified
- test_delay_increases_exponentially: mock time.sleep, verify delays are 0.01, 0.02, 0.04
- test_no_delay_on_success: mock time.sleep, verify not called if first attempt succeeds
```

## Architecture

```
spec/
├── __init__.py
├── parser.py       # Parse spec markdown → SpecDocument dataclass
├── generator.py    # SpecDocument → Python implementation via Claude
├── runner.py       # Write files to temp dir, run pytest, capture output
├── feedback.py     # Parse pytest failure output → structured feedback
├── loop.py         # Orchestrate: generate → test → feedback → retry
└── cli.py          # `spec run <spec.md>` command

specs/
├── retry_with_backoff.md   # example spec
├── lru_cache.md
└── rate_limiter.md

tests_generated/            # auto-generated, gitignored
output/                     # final passing implementations
│── retry_with_backoff.py

pyproject.toml
README.md
```

## Implementation Phases

### Phase 1: Spec parser (parser.py)

Parse a spec markdown file into a structured Python object.

```python
@dataclass
class SpecDocument:
    name: str                    # from H1: "retry_with_backoff"
    description: str             # ## Description section
    signature: str               # ## Signature code block
    behavior: list[str]          # ## Behavior bullet points
    examples: list[str]          # ## Examples code blocks
    test_names: list[str]        # ## Tests bullet points (test function names)
    raw_markdown: str            # full original spec
```

Use Python's `re` and simple state-machine parsing — no heavy markdown library.

### Phase 2: Test generator (generator.py — tests first)

Before generating the implementation, generate the test file from the spec. Tests are easier to generate reliably because the spec's `## Tests` section names them explicitly.

```python
test_code = generator.generate_tests(spec)
# → produces test_retry_with_backoff.py with all named test functions
```

This is TDD: we have a test file before any implementation.

### Phase 3: Implementation generator (generator.py — implementation)

Generate the implementation from the spec. Key prompt engineering:
- Include the signature verbatim (exact function name, args, types)
- Include behavior bullets as a numbered list
- Include examples as doctest-style expected behavior
- Explicitly instruct: "output ONLY the Python code, no explanation"

```python
impl_code = generator.generate_implementation(spec, previous_attempt=None, feedback=None)
```

### Phase 4: Test runner (runner.py)

Write the generated files to a temp directory and run pytest.

```
temp_dir/
├── {spec.name}.py          # generated implementation
├── test_{spec.name}.py     # generated tests
└── conftest.py             # minimal pytest config
```

```python
result = runner.run(impl_code, test_code)
# → RunResult: passed, failed, errors, stdout, duration
```

Timeout: 30 seconds. Any test hanging longer = mark as failed.

### Phase 5: Feedback parser (feedback.py)

Parse pytest's output into structured feedback for the next generation attempt.

```python
feedback = feedback_parser.parse(pytest_stdout)
# → Feedback:
#     failing_tests: list[FailingTest]
#       - test_name: "test_delay_increases_exponentially"
#       - assertion_error: "assert sleep.call_args_list == [call(0.01), call(0.02), call(0.04)]"
#       - actual: "call_args_list was [call(1.0), call(2.0), call(4.0)]"
```

This structured feedback is what gets sent back to Claude for the next attempt — not the raw pytest output.

### Phase 6: Iteration loop (loop.py)

```python
for attempt in range(1, max_attempts + 1):
    impl = generator.generate_implementation(spec, attempt, feedback)
    result = runner.run(impl, test_code)

    if result.all_passed:
        return Success(impl, attempts=attempt)

    feedback = feedback_parser.parse(result.stdout)
    log_attempt(attempt, result, feedback)

return Failure(best_attempt, all_feedback)
```

Key: each attempt includes ALL previous feedback in the prompt (not just the last one). Claude sees the full correction history.

### Phase 7: CLI

```bash
# Run a spec
spec run specs/retry_with_backoff.md
# → Attempt 1: 3/5 tests passing
# → Attempt 2: 4/5 tests passing
# → Attempt 3: 5/5 tests passing ✓
# → Saved to output/retry_with_backoff.py

# Run with verbose output (show generated code each attempt)
spec run specs/retry_with_backoff.md --verbose

# Run all specs in directory
spec run specs/ --parallel

# Show stats across all runs
spec stats
# → retry_with_backoff: passed on attempt 2 (avg: 1.8)
# → lru_cache: passed on attempt 1
# → rate_limiter: failed after 3 attempts
```

### Phase 8: Write a spec library

Write 10 specs for real utility functions. Run all of them. Document:
- Which passed on first attempt?
- Which required iteration? What kind of feedback helped?
- Which never passed? Why?

Suggested specs:
1. `retry_with_backoff`
2. `lru_cache` (from scratch, not `functools`)
3. `rate_limiter` (token bucket algorithm)
4. `circuit_breaker` (open/closed/half-open states)
5. `event_emitter` (subscribe/emit/unsubscribe)
6. `bounded_queue` (thread-safe, blocking put/get)
7. `debounce` (decorator, delay + cancel)
8. `memoize_to_disk` (persistent cache with TTL)
9. `diff_json` (deep diff two JSON objects)
10. `topological_sort` (Kahn's algorithm)

## Key Design Decisions

**Why generate tests first, then implementation?**
Tests are more constrained by the spec (exact function names, exact expected values). Generating tests first creates a stable target. If we generate implementation first, we risk generating tests that confirm the implementation rather than the spec.

**Why include ALL previous feedback in the retry prompt?**
Claude can and does make the same mistake twice if it only sees the last failure. The full history prevents regression ("I fixed test 3 but broke test 1 again").

**Why pytest and not a custom test runner?**
Pytest output is rich, standard, and Claude already "knows" how to read it. Using pytest means the feedback parser is well-defined and we can test it against real pytest output.

**What we're NOT building**
- Multi-file implementations (one spec → one file)
- Non-Python languages (follow-on)
- Spec generation from existing code (inverse problem, follow-on)

## Acceptance Criteria

1. ≥7/10 specs from the library pass within 3 attempts
2. First-attempt pass rate ≥4/10 (measures spec clarity + prompt quality)
3. Feedback parser correctly extracts failing test names and assertion errors from real pytest output
4. `spec stats` shows per-spec attempt counts and pass/fail
5. Full run of 10 specs documented in `RESULTS.md` with analysis

## Learning Outcomes

After building this you will understand:
- Why spec quality is now the core engineering skill (you'll feel it when your spec is ambiguous)
- How test-driven generation differs from test-driven development
- What structured feedback looks like vs. raw error output (why parsing matters)
- The self-correction loop failure modes: why some specs never converge
- The gap between "model understood" and "model can implement reliably"
