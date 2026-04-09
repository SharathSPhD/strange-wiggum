# C06 — Adaptive Sort Selector

## Task

Implement `adaptive_sort(arr: list) -> list` that:
1. Empirically benchmarks merge sort vs quicksort on the given input
2. Returns the sorted array using whichever algorithm was faster on that input
3. Also returns which algorithm was chosen

Signature:
```python
def adaptive_sort(arr: list) -> tuple[list, str]:
    """Returns (sorted_list, algorithm_name) where algorithm_name is 'mergesort' or 'quicksort'."""
```

Requirements:
- Implement both sorting algorithms from scratch (no `sorted()` for the actual sort — only for verification)
- Both implementations must sort correctly for all inputs
- The benchmark must time actual sorting runs (not just estimate)
- For arrays < 10 elements, skip benchmarking and use mergesort directly
- Handle edge cases: empty list, single element, all duplicates, already sorted, reverse sorted

Output your COMPLETE solution as a single ```python code block in your TEXT RESPONSE (do not use any file tools). When complete: <promise>TASK COMPLETE</promise>

## Test Suite (pytest)

```python
# test_C06.py
import pytest
from solution import adaptive_sort

def test_empty():
    result, algo = adaptive_sort([])
    assert result == [] and algo == "mergesort"

def test_single():
    result, algo = adaptive_sort([42])
    assert result == [42]

def test_correctness_random():
    import random; random.seed(42)
    arr = [random.randint(0, 1000) for _ in range(500)]
    result, algo = adaptive_sort(arr)
    assert result == sorted(arr)
    assert algo in ("mergesort", "quicksort")

def test_correctness_duplicates():
    arr = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]
    result, _ = adaptive_sort(arr)
    assert result == sorted(arr)

def test_correctness_already_sorted():
    arr = list(range(100))
    result, _ = adaptive_sort(arr)
    assert result == arr

def test_correctness_reverse():
    arr = list(range(100, 0, -1))
    result, _ = adaptive_sort(arr)
    assert result == sorted(arr)

def test_small_uses_mergesort():
    _, algo = adaptive_sort([3, 1, 2])
    assert algo == "mergesort"
```
