# Spec: topological_sort

## Description
Topological sort using Kahn's algorithm. Takes a directed acyclic graph
represented as an adjacency list and returns nodes in a valid topological
order. Raises an error if the graph contains a cycle.

## Signature
```python
def topological_sort(graph: dict[str, list[str]]) -> list[str]:
```

## Behavior
- `graph` is a dict mapping each node to a list of nodes it has edges TO (dependencies point from dependent to dependency)
- Returns a list of all nodes in a valid topological order (every node appears before all nodes it points to)
- If the graph is empty, return an empty list
- All nodes referenced in edge lists must also be keys in the graph dict; if a target node is not a key, treat it as a node with no outgoing edges
- If the graph contains a cycle, raise `CycleError` with a message that includes at least one node involved in the cycle
- `CycleError` is a custom exception class defined in the same module
- When multiple valid orderings exist, prefer alphabetical order among equally-valid choices (use a min-heap or sorted collection for the queue)
- Uses Kahn's algorithm: compute in-degrees, start with zero in-degree nodes, repeatedly remove and process them

## Examples
```python
graph = {
    "a": ["b", "c"],
    "b": ["d"],
    "c": ["d"],
    "d": [],
}
assert topological_sort(graph) == ["a", "b", "c", "d"]
```

```python
graph = {"a": ["b"], "b": ["a"]}
# Raises CycleError
```

## Tests
- test_linear_chain: a -> b -> c -> d returns [a, b, c, d]
- test_diamond: diamond dependency graph returns valid order
- test_cycle_raises: graph with cycle raises CycleError
- test_empty_graph: empty dict returns empty list
- test_deterministic_order: among equally-valid nodes, alphabetical order is used
