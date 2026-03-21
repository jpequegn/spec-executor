# Spec: circuit_breaker

## Description
A circuit breaker that wraps a callable. Tracks consecutive failures and
transitions between closed (allowing calls), open (blocking calls), and
half-open (allowing a single test call) states.

## Signature
```python
class circuit_breaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 5.0) -> None: ...
    def call(self, func: Callable, *args, **kwargs) -> object: ...
    @property
    def state(self) -> str: ...
```

## Behavior
- Starts in "closed" state (calls pass through normally)
- In "closed" state: if `func` raises an exception, increment failure counter; if it succeeds, reset failure counter to 0
- When failure counter reaches `failure_threshold`, transition to "open" state and record the time
- In "open" state: `call()` raises `CircuitOpenError` without invoking `func`
- After `recovery_timeout` seconds in "open" state, transition to "half-open" state
- In "half-open" state: allow exactly one call through. If it succeeds, transition to "closed" and reset failure counter. If it fails, transition back to "open" and reset the timer
- `state` property returns one of: "closed", "open", "half-open"
- `CircuitOpenError` is a custom exception class defined in the same module
- Uses `time.monotonic()` for time tracking

## Examples
```python
cb = circuit_breaker(failure_threshold=2, recovery_timeout=1.0)
assert cb.state == "closed"

# Two failures trip the breaker
try: cb.call(failing_func)
except ValueError: pass
try: cb.call(failing_func)
except ValueError: pass
assert cb.state == "open"
```

## Tests
- test_starts_closed: initial state is "closed"
- test_passes_through_on_success: successful calls return the result
- test_opens_after_threshold: consecutive failures transition to "open"
- test_blocks_in_open_state: raises CircuitOpenError without calling func
- test_half_open_after_timeout: transitions to "half-open" after recovery_timeout (mock time.monotonic)
