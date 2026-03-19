# Spec: rate_limiter

## Description
A token bucket rate limiter. Tokens are added at a fixed rate up to a maximum
bucket size. Each request consumes one token. If no tokens are available, the
request is rejected.

## Signature
```python
class rate_limiter:
    def __init__(self, rate: float, capacity: int) -> None: ...
    def allow(self) -> bool: ...
    def tokens(self) -> float: ...
```

## Behavior
- `__init__` creates a rate limiter with `rate` tokens added per second and a maximum `capacity`
- The bucket starts full (tokens equal to capacity)
- `allow()` returns True and consumes one token if at least one token is available
- `allow()` returns False if no tokens are available
- Tokens are refilled based on elapsed time since last check: `elapsed * rate`, capped at `capacity`
- Token count can be fractional internally but `allow()` requires at least 1.0 token
- `tokens()` returns the current number of tokens (after refill calculation) as a float
- Uses `time.monotonic()` for time tracking

## Examples
```python
limiter = rate_limiter(rate=10.0, capacity=5)
# Starts with 5 tokens
assert limiter.allow() is True  # 4 tokens left
assert limiter.allow() is True  # 3 tokens left
```

```python
limiter = rate_limiter(rate=1.0, capacity=1)
assert limiter.allow() is True   # 0 tokens left
assert limiter.allow() is False  # no tokens
```

## Tests
- test_starts_full: new limiter allows up to capacity requests
- test_rejects_when_empty: returns False after all tokens consumed
- test_refills_over_time: after waiting, tokens are replenished (mock time.monotonic)
- test_capacity_cap: tokens never exceed capacity even after long wait
- test_tokens_returns_current_count: tokens() reflects remaining tokens after allow() calls
