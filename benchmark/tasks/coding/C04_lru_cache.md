# C04 — LRU Cache O(1)

## Task

Implement an `LRUCache` class with O(1) `get` and `put` operations.

```
LRUCache(capacity: int)
get(key: int) -> int          # return value or -1 if not found
put(key: int, value: int)     # insert/update; evict LRU if at capacity
```

Requirements:
- O(1) for both `get` and `put` (use doubly-linked list + hashmap)
- Most recently used item is kept; least recently used is evicted when full
- `get` counts as a use (moves item to most-recently-used position)
- Do NOT use `functools.lru_cache` or `collections.OrderedDict` as the primary structure
  (you may use OrderedDict only if you implement it yourself first and then refactor)

Output your COMPLETE solution as a single ```python code block in your TEXT RESPONSE (do not use any file tools). When complete: <promise>TASK COMPLETE</promise>

## Test Suite (pytest)

```python
# test_C04.py
import pytest
from solution import LRUCache

def test_basic():
    cache = LRUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    assert cache.get(1) == 1
    cache.put(3, 3)        # evicts key 2 (LRU)
    assert cache.get(2) == -1
    assert cache.get(3) == 3

def test_update_refreshes_lru():
    cache = LRUCache(2)
    cache.put(1, 1); cache.put(2, 2)
    cache.put(1, 10)       # update key 1 → now MRU
    cache.put(3, 3)        # evicts key 2 (LRU)
    assert cache.get(1) == 10
    assert cache.get(2) == -1

def test_get_refreshes_lru():
    cache = LRUCache(2)
    cache.put(1, 1); cache.put(2, 2)
    cache.get(1)           # key 1 now MRU
    cache.put(3, 3)        # evicts key 2
    assert cache.get(1) == 1
    assert cache.get(2) == -1

def test_capacity_one():
    cache = LRUCache(1)
    cache.put(1, 1)
    cache.put(2, 2)
    assert cache.get(1) == -1
    assert cache.get(2) == 2

def test_miss_returns_minus_one():
    cache = LRUCache(3)
    assert cache.get(999) == -1
```
