# Spec: lru_cache

## Description
A class implementing a least-recently-used cache with a fixed maximum size.
When the cache is full and a new key is inserted, the least recently accessed
key is evicted. Both get and put operations count as access.

## Signature
```python
class lru_cache:
    def __init__(self, capacity: int) -> None: ...
    def get(self, key: str) -> object | None: ...
    def put(self, key: str, value: object) -> None: ...
    def size(self) -> int: ...
```

## Behavior
- `__init__` creates an empty cache with the given maximum capacity
- `get(key)` returns the value if key exists, otherwise returns None
- `get(key)` marks the key as most recently used
- `put(key, value)` inserts or updates the key-value pair
- `put(key, value)` marks the key as most recently used
- When cache is full and a new key is inserted, the least recently used key is evicted
- Updating an existing key does NOT count as inserting a new key (no eviction needed)
- `size()` returns the current number of items in the cache
- Do NOT use functools.lru_cache; implement from scratch using OrderedDict or similar

## Examples
```python
cache = lru_cache(2)
cache.put("a", 1)
cache.put("b", 2)
assert cache.get("a") == 1  # "a" is now most recently used
cache.put("c", 3)           # evicts "b" (least recently used)
assert cache.get("b") is None
assert cache.get("c") == 3
```

## Tests
- test_get_and_put: basic insert and retrieve
- test_eviction_on_capacity: inserting beyond capacity evicts LRU key
- test_get_updates_recency: accessing a key prevents it from being evicted
- test_update_existing_key: updating existing key does not evict anything
- test_size: size reflects current item count
