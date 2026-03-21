# Spec: memoize_to_disk

## Description
A decorator that caches function results to disk as JSON files. Each unique
set of arguments produces a separate cache file. Supports TTL-based expiration.

## Signature
```python
def memoize_to_disk(cache_dir: str = ".cache", ttl: float | None = None) -> Callable:
```

## Behavior
- Returns a decorator that wraps a function with disk-based memoization
- Cache files are stored in `cache_dir` directory (created if it doesn't exist)
- Cache key is derived from function name and arguments: `{func_name}_{hash}.json` where hash is a SHA-256 hex digest of the JSON-serialized arguments (first 16 chars)
- Cache file contains JSON with keys: `"result"`, `"timestamp"` (Unix epoch float), `"args"`, `"kwargs"`
- On cache hit (file exists and not expired): return cached result without calling function
- On cache miss (file missing or expired): call function, store result, return it
- If `ttl` is None, cache never expires
- If `ttl` is a number, cache expires after `ttl` seconds (compare current time minus stored timestamp)
- Arguments must be JSON-serializable; raise `TypeError` if they are not
- The decorated function has a `clear_cache()` method that deletes all cache files for that function
- Uses `time.time()` for timestamps

## Examples
```python
@memoize_to_disk(cache_dir="/tmp/test_cache", ttl=60)
def expensive(x):
    return x * 2

assert expensive(5) == 10  # computed and cached
assert expensive(5) == 10  # returned from cache
```

## Tests
- test_caches_result: second call returns cached value without re-executing function
- test_ttl_expiration: expired cache triggers re-execution (mock time.time)
- test_different_args_different_cache: different arguments produce different cache entries
- test_clear_cache: clear_cache() removes all cache files for the function
- test_non_serializable_args_raises: passing non-JSON-serializable args raises TypeError
