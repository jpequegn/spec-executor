# Spec: retry_with_backoff

## Description
A function decorator that retries the wrapped function on exception,
with exponential backoff between attempts.

## Signature
```python
def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple[type[Exception], ...] = (Exception,)
) -> Callable:
```

## Behavior
- Retries up to `max_retries` times on any exception whose type is in `exceptions`
- Waits `base_delay * 2^attempt` seconds between attempts, where attempt is 0-indexed (first retry has attempt=0)
- On final failure (after all retries exhausted), re-raises the original exception unchanged
- Does NOT retry if the raised exception type is not in `exceptions`; raises it immediately
- Logs each retry attempt to stdout with format: `Retry {attempt+1}/{max_retries} after {delay}s`

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

```python
# Raises after exhaustion
@retry_with_backoff(max_retries=2, base_delay=0.01, exceptions=(ValueError,))
def always_fails():
    raise ValueError("always")

# Calling always_fails() raises ValueError("always")
```

```python
# No retry on wrong exception type
@retry_with_backoff(max_retries=3, base_delay=0.01, exceptions=(ValueError,))
def wrong_type():
    raise TypeError("wrong")

# Calling wrong_type() raises TypeError("wrong") immediately, no retries
```

## Tests
- test_succeeds_on_final_attempt: function fails twice then succeeds on 3rd call; returns correct value
- test_raises_after_exhaustion: function always raises ValueError; after max_retries, ValueError is re-raised
- test_no_retry_on_wrong_exception_type: function raises TypeError but only ValueError in exceptions tuple; TypeError raised immediately with no retries
- test_delay_is_exponential: mock time.sleep; with base_delay=0.01 and 3 retries, verify sleep called with 0.01, 0.02, 0.04
- test_no_delay_on_first_success: mock time.sleep; function succeeds on first call; time.sleep never called
