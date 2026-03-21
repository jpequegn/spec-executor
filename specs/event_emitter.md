# Spec: event_emitter

## Description
An event system supporting subscribe, emit, and unsubscribe. Handlers are
called in registration order. Supports multiple handlers per event and
one-time handlers.

## Signature
```python
class event_emitter:
    def __init__(self) -> None: ...
    def on(self, event: str, handler: Callable) -> None: ...
    def once(self, event: str, handler: Callable) -> None: ...
    def emit(self, event: str, *args, **kwargs) -> None: ...
    def off(self, event: str, handler: Callable) -> None: ...
    def listeners(self, event: str) -> list[Callable]: ...
```

## Behavior
- `on(event, handler)` registers a handler for the event; same handler can be registered multiple times
- `once(event, handler)` registers a handler that is automatically removed after the first time it is called
- `emit(event, *args, **kwargs)` calls all registered handlers for the event in registration order, passing args and kwargs
- `emit` on an event with no handlers does nothing (no error)
- `off(event, handler)` removes the first occurrence of handler for the event; raises ValueError if handler is not registered
- `listeners(event)` returns a list of currently registered handlers for the event (excluding already-fired once handlers)

## Examples
```python
ee = event_emitter()
results = []
ee.on("data", lambda x: results.append(x))
ee.emit("data", 42)
assert results == [42]
```

```python
ee = event_emitter()
results = []
ee.once("ping", lambda: results.append("pong"))
ee.emit("ping")
ee.emit("ping")
assert results == ["pong"]  # only called once
```

## Tests
- test_on_and_emit: handler receives emitted arguments
- test_multiple_handlers: handlers called in registration order
- test_once_fires_once: once handler removed after first emit
- test_off_removes_handler: unsubscribed handler is not called
- test_off_nonexistent_raises: off with unregistered handler raises ValueError
