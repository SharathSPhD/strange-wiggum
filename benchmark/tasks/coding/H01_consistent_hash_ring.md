# H01 — Consistent Hash Ring

## Task

Implement a **consistent hash ring** with virtual nodes. Consistent hashing is the algorithm behind distributed key-value stores (Dynamo, Cassandra, Chord) — it routes keys to nodes such that adding or removing a node only redistributes `k/n` keys on average (not all keys).

## Requirements

Implement a class `ConsistentHashRing` in `solution.py`:

```python
class ConsistentHashRing:
    def __init__(self, virtual_nodes: int = 150): ...
    def add_node(self, node_id: str) -> None: ...
    def remove_node(self, node_id: str) -> None: ...
    def get_node(self, key: str) -> str: ...
    def get_all_nodes(self) -> list[str]: ...
```

### Behaviour

- `__init__(virtual_nodes)`: Create an empty ring. `virtual_nodes` is how many virtual positions each physical node occupies on the ring (default 150).
- `add_node(node_id)`: Add a physical node to the ring. Each call places `virtual_nodes` hash positions for that node. If the node is already present, do nothing.
- `remove_node(node_id)`: Remove all virtual positions for a node. If the node is not present, do nothing.
- `get_node(key)`: Hash `key` and walk clockwise on the ring to find the first virtual node; return its physical `node_id`. Raise `LookupError` if the ring is empty.
- `get_all_nodes()`: Return a sorted list of all currently registered physical node IDs (no duplicates).

### Hashing

Use `hashlib.md5` (or `hashlib.sha1`) to convert strings to ring positions. A good virtual node label is `f"{node_id}#{i}"` for `i` in `range(virtual_nodes)`.

### Constraints

- Do NOT use any third-party libraries (`uhashring`, `pyhash`, etc.). Only stdlib.
- All methods must be O(log n) or better in the number of virtual nodes for `get_node`.
- Duplicate `add_node` calls for the same node must be idempotent.

## Test Suite

```python
# test_solution
import hashlib
import pytest
from solution import ConsistentHashRing


def test_single_node_always_returns_it():
    ring = ConsistentHashRing(virtual_nodes=50)
    ring.add_node("A")
    for key in ["foo", "bar", "baz", "x" * 100, ""]:
        assert ring.get_node(key) == "A"


def test_empty_ring_raises():
    ring = ConsistentHashRing()
    with pytest.raises(LookupError):
        ring.get_node("anything")


def test_get_all_nodes_sorted():
    ring = ConsistentHashRing()
    ring.add_node("node-C")
    ring.add_node("node-A")
    ring.add_node("node-B")
    assert ring.get_all_nodes() == ["node-A", "node-B", "node-C"]


def test_remove_node_empty_ring_no_error():
    ring = ConsistentHashRing()
    ring.remove_node("ghost")  # must not raise


def test_remove_node_routes_elsewhere():
    ring = ConsistentHashRing(virtual_nodes=200)
    ring.add_node("alpha")
    ring.add_node("beta")
    ring.add_node("gamma")
    # Find which node "mykey" lands on
    original = ring.get_node("mykey")
    ring.remove_node(original)
    # After removal it must go to one of the remaining nodes
    remaining = set(ring.get_all_nodes())
    assert original not in remaining
    new_node = ring.get_node("mykey")
    assert new_node in remaining


def test_add_node_idempotent():
    ring = ConsistentHashRing(virtual_nodes=50)
    ring.add_node("dup")
    ring.add_node("dup")
    assert ring.get_all_nodes() == ["dup"]
    # Should still route correctly
    assert ring.get_node("anything") == "dup"


def test_distribution_uniformity():
    """Virtual nodes should spread load roughly evenly."""
    import random
    random.seed(42)
    ring = ConsistentHashRing(virtual_nodes=150)
    nodes = ["node-1", "node-2", "node-3", "node-4"]
    for n in nodes:
        ring.add_node(n)

    counts = {n: 0 for n in nodes}
    for i in range(10_000):
        key = str(random.random())
        counts[ring.get_node(key)] += 1

    mean = 10_000 / len(nodes)
    for n, c in counts.items():
        # Each node should receive between 50% and 200% of the mean
        assert 0.5 * mean < c < 2.0 * mean, (
            f"Node {n} got {c} keys (mean={mean:.0f}) — distribution too skewed"
        )


def test_round_trip_add_remove_add():
    ring = ConsistentHashRing(virtual_nodes=100)
    ring.add_node("X")
    ring.add_node("Y")
    node_for_key = ring.get_node("test-key")
    ring.remove_node(node_for_key)
    ring.add_node(node_for_key)
    # After re-adding, the same key should map back to the same node
    assert ring.get_node("test-key") == node_for_key
```

## Notes

- The solution must not import or use any ring/hashing library — build it from scratch with `hashlib` and `bisect`.
- The distribution test uses `virtual_nodes=150` and 10,000 keys — with fewer virtual nodes the variance will be too high and the test will fail.
- Do not use any file tools; output only valid Python.
