# Spec: debounce

## Description
A decorator that delays execution of the wrapped function. If the function
is called again within the delay window, the previous pending call is cancelled
and the timer resets. Uses threading for the delay.

## Signature
```python
def debounce(delay: float) -> Callable:
```

## Behavior
- Returns a decorator that wraps a function with debounce behavior
- When the wrapped function is called, it does NOT execute immediately
- Instead, it schedules execution after `delay` seconds
- If the wrapped function is called again before `delay` has elapsed, the previous pending call is cancelled and a new timer starts
- The function is called with the arguments from the LAST call (not the first)
- Uses `threading.Timer` for scheduling
- The decorated function has a `cancel()` method to cancel any pending call
- The decorated function has a `flush()` method that immediately executes the pending call (if any) and cancels the timer
- Thread-safe: concurrent calls are handled correctly

## Examples
```python
results = []

@debounce(0.1)
def save(value):
    results.append(value)

save("a")
save("b")  # cancels "a", schedules "b"
time.sleep(0.2)
assert results == ["b"]
```

## Tests
- test_delays_execution: function not called immediately, called after delay
- test_cancels_previous: rapid calls result in only the last call executing
- test_uses_last_args: debounced call uses arguments from the most recent invocation
- test_cancel_method: cancel() prevents pending execution
- test_flush_method: flush() immediately executes pending call
