# Spec: diff_json

## Description
Deep diff two JSON-serializable Python objects. Returns a list of changes
describing what was added, removed, or modified between the two objects.

## Signature
```python
def diff_json(old: object, new: object, path: str = "") -> list[dict]:
```

## Behavior
- Compares `old` and `new` recursively and returns a list of change dicts
- Each change dict has keys: `"op"` (one of "add", "remove", "change"), `"path"` (dot-separated path string), and relevant value keys
- For `"add"`: `{"op": "add", "path": "...", "value": new_value}`
- For `"remove"`: `{"op": "remove", "path": "...", "value": old_value}`
- For `"change"`: `{"op": "change", "path": "...", "old": old_value, "new": new_value}`
- Path uses dot notation for dict keys and bracket notation for list indices: e.g., `"users[0].name"`
- Root-level path is an empty string `""`
- Dict comparison: keys in new but not old are "add"; keys in old but not new are "remove"; keys in both with different values are recursed
- List comparison: compares element by element up to the length of the shorter list; extra elements in new are "add"; extra elements in old are "remove"
- Scalar comparison (str, int, float, bool, None): if not equal, produce a "change" entry
- If old and new are equal (deeply), return an empty list
- If old and new are different types at the same path, produce a "change" entry (do not recurse)

## Examples
```python
old = {"name": "Alice", "age": 30}
new = {"name": "Alice", "age": 31, "city": "NYC"}
result = diff_json(old, new)
# [{"op": "change", "path": "age", "old": 30, "new": 31},
#  {"op": "add", "path": "city", "value": "NYC"}]
```

## Tests
- test_no_changes: identical objects return empty list
- test_scalar_change: top-level value change detected
- test_nested_dict_change: change in nested dict uses dot path
- test_list_add_remove: extra/missing list elements detected with bracket notation
- test_type_mismatch: different types at same path produce "change" not recursion
