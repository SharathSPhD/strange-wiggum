# H03 — LFU Cache

## Task

Implement an **LFU (Least Frequently Used) cache**. LFU evicts the item that has been accessed the *fewest times*. When there is a tie in frequency, evict the item that was *least recently used* among the tied items (LRU tie-breaking).

LFU is a superset of LRU — it is strictly harder to implement correctly and efficiently. Both `get` and `put` must run in **O(1)** time.

## Requirements

Implement a class `LFUCache` in `solution.py`:

```python
class LFUCache:
    def __init__(self, capacity: int): ...
    def get(self, key: int) -> int: ...
    def put(self, key: int, value: int) -> None: ...
```

### Behaviour

- `__init__(capacity)`: Create a cache with the given max capacity. `capacity >= 1`.
- `get(key)`: Return the value associated with `key` if it exists; otherwise return `-1`. **Accessing a key via `get` increases its frequency by 1.**
- `put(key, value)`: Insert or update `key` with `value`.
  - If `key` already exists: update the value and **increase its frequency by 1**.
  - If `key` does not exist and capacity is full: **evict** the key with the lowest frequency. If multiple keys share the lowest frequency, evict the one that was least recently used (inserted/accessed least recently among them). Then insert the new key with frequency 1.
  - If `key` does not exist and there is space: insert with frequency 1.

### O(1) requirement

A correct O(1) LFU uses:
- A `key → (value, freq)` hashmap
- A `freq → OrderedDict[key, None]` hashmap (ordered = LRU order within same freq)
- A `min_freq` tracker

Simpler O(n) approaches (scanning all keys to find min freq) are accepted for partial credit but will likely score lower on the judge's efficiency dimension.

### Constraints

- stdlib only (`collections.OrderedDict` or `collections.defaultdict` are fine).
- `capacity` is always ≥ 1.
- Keys and values are integers.
- Do not use any file tools; output only valid Python.

## Test Suite

```python
# test_solution
import pytest
from solution import LFUCache


def test_basic_get_put():
    cache = LFUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    assert cache.get(1) == 1
    assert cache.get(2) == 2
    assert cache.get(3) == -1


def test_evict_lfu():
    """Key 1 is less frequent than key 2 — evict key 1."""
    cache = LFUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    cache.get(2)   # freq(1)=1, freq(2)=2
    cache.put(3, 3)  # evicts key 1 (lowest freq)
    assert cache.get(1) == -1
    assert cache.get(2) == 2
    assert cache.get(3) == 3


def test_lru_tiebreak():
    """Keys 1 and 2 both have freq=1; key 1 was inserted first — evict key 1."""
    cache = LFUCache(2)
    cache.put(1, 10)
    cache.put(2, 20)
    cache.put(3, 30)  # evicts key 1 (same freq=1, key 1 is LRU)
    assert cache.get(1) == -1
    assert cache.get(2) == 20
    assert cache.get(3) == 30


def test_update_existing_key():
    cache = LFUCache(2)
    cache.put(1, 100)
    cache.put(1, 200)   # update: value changes, freq increments
    assert cache.get(1) == 200


def test_capacity_one():
    cache = LFUCache(1)
    cache.put(1, 1)
    assert cache.get(1) == 1
    cache.put(2, 2)   # evicts key 1
    assert cache.get(1) == -1
    assert cache.get(2) == 2


def test_get_promotes_frequency():
    """After get, key should not be evicted before a less-accessed key."""
    cache = LFUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    cache.get(1)   # freq(1)=2, freq(2)=1
    cache.put(3, 3)  # must evict key 2 (freq=1), not key 1 (freq=2)
    assert cache.get(1) == 1
    assert cache.get(2) == -1
    assert cache.get(3) == 3


def test_multi_eviction_sequence():
    """Extended sequence to verify frequency accounting is cumulative."""
    cache = LFUCache(3)
    cache.put(1, 1)
    cache.put(2, 2)
    cache.put(3, 3)
    cache.get(1)   # freq: 1→2, 2→1, 3→1
    cache.get(1)   # freq: 1→3, 2→1, 3→1
    cache.get(2)   # freq: 1→3, 2→2, 3→1
    cache.put(4, 4)  # evicts key 3 (freq=1, only candidate)
    assert cache.get(3) == -1
    cache.put(5, 5)  # evicts key 2 (freq=2) — wait: freq(2)=2, freq(4)=1
    # Actually key 4 has freq=1, so evict key 4
    assert cache.get(4) == -1
    assert cache.get(1) == 1
    assert cache.get(2) == 2
    assert cache.get(5) == 5


def test_lru_tiebreak_after_get():
    """
    Three keys all at freq=1. The one accessed most recently should survive.
    """
    cache = LFUCache(3)
    cache.put(1, 1)
    cache.put(2, 2)
    cache.put(3, 3)
    # Access key 2, then key 3, then key 1 — making key 1 the most recently used at freq=1
    cache.get(2)  # now freq(2)=2; 1 and 3 remain at freq=1
    # 1 was inserted first (LRU among freq=1), so adding key 4 evicts key 1
    cache.put(4, 4)
    assert cache.get(1) == -1
    assert cache.get(2) == 2
    assert cache.get(3) == 3
    assert cache.get(4) == 4
```

## Notes

- The O(1) solution requires `collections.OrderedDict` to maintain insertion order within each frequency bucket, enabling O(1) LRU eviction within a frequency level.
- `min_freq` must be updated on every `put` (new key → min_freq=1) and on every `get`/update (if the old freq was min_freq and that bucket is now empty, increment min_freq).
- Do not use any file tools; output only valid Python.
