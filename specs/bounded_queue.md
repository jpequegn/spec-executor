# Spec: bounded_queue

## Description
A thread-safe blocking queue with a maximum size. Put blocks when full,
get blocks when empty, with optional timeouts on both operations.

## Signature
```python
class bounded_queue:
    def __init__(self, maxsize: int) -> None: ...
    def put(self, item: object, timeout: float | None = None) -> None: ...
    def get(self, timeout: float | None = None) -> object: ...
    def size(self) -> int: ...
    def empty(self) -> bool: ...
    def full(self) -> bool: ...
```

## Behavior
- `__init__` creates an empty queue with the given maximum size
- `put(item)` adds item to the queue; blocks if queue is full until space is available
- `put(item, timeout=N)` blocks for at most N seconds; raises `QueueFullError` if still full after timeout
- `get()` removes and returns the oldest item; blocks if queue is empty until an item is available
- `get(timeout=N)` blocks for at most N seconds; raises `QueueEmptyError` if still empty after timeout
- `size()` returns current number of items
- `empty()` returns True if queue has no items
- `full()` returns True if queue has reached maxsize
- `QueueFullError` and `QueueEmptyError` are custom exceptions defined in the same module
- Must be thread-safe: use `threading.Lock` and `threading.Condition`
- Items are returned in FIFO order

## Examples
```python
q = bounded_queue(2)
q.put("a")
q.put("b")
assert q.full() is True
assert q.get() == "a"  # FIFO
```

## Tests
- test_fifo_order: items returned in insertion order
- test_blocks_when_full: put with timeout raises QueueFullError on full queue
- test_blocks_when_empty: get with timeout raises QueueEmptyError on empty queue
- test_thread_safety: concurrent put and get from multiple threads
- test_size_empty_full: size/empty/full reflect queue state correctly
