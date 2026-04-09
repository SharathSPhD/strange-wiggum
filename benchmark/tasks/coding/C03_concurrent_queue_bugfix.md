# C03 — Fix Buggy Concurrent Queue

## Task

The following `BoundedQueue` implementation has **3 bugs** that cause race conditions or
incorrect behaviour under concurrent access. Find and fix all 3 bugs.

```python
# buggy_queue.py
import threading

class BoundedQueue:
    """A thread-safe bounded queue. Max capacity = maxsize."""

    def __init__(self, maxsize: int):
        self.maxsize = maxsize
        self._queue = []
        self._lock = threading.Lock()
        self._not_full = threading.Condition()   # BUG 1
        self._not_empty = threading.Condition()  # BUG 1

    def put(self, item, timeout=None):
        with self._not_full:
            while len(self._queue) >= self.maxsize:
                if not self._not_full.wait(timeout):
                    raise TimeoutError("Queue is full")
            self._queue.append(item)
            self._not_empty.notify()             # BUG 2

    def get(self, timeout=None):
        with self._not_empty:
            while len(self._queue) == 0:
                if not self._not_empty.wait(timeout):
                    raise TimeoutError("Queue is empty")
            item = self._queue[0]                # BUG 3
            self._not_full.notify()              # BUG 2
        return item

    def qsize(self):
        return len(self._queue)
```

Fix the bugs. Output the corrected solution as a single ```python code block in your TEXT RESPONSE (do not use any file tools) with inline comments marking each fix.
When complete: <promise>TASK COMPLETE</promise>

## Test Suite (pytest)

```python
# test_C03.py
import threading, pytest
from solution import BoundedQueue

def test_basic_put_get():
    q = BoundedQueue(3)
    q.put(1); q.put(2)
    assert q.get() == 1
    assert q.get() == 2

def test_fifo_order():
    q = BoundedQueue(5)
    for i in range(5): q.put(i)
    assert [q.get() for _ in range(5)] == list(range(5))

def test_full_raises_timeout():
    q = BoundedQueue(2)
    q.put("a"); q.put("b")
    with pytest.raises(TimeoutError):
        q.put("c", timeout=0.05)

def test_empty_raises_timeout():
    q = BoundedQueue(2)
    with pytest.raises(TimeoutError):
        q.get(timeout=0.05)

def test_concurrent_producers_consumers():
    q = BoundedQueue(10)
    results = []
    def producer():
        for i in range(50): q.put(i)
    def consumer():
        for _ in range(50): results.append(q.get())
    t1 = threading.Thread(target=producer)
    t2 = threading.Thread(target=consumer)
    t1.start(); t2.start()
    t1.join(); t2.join()
    assert len(results) == 50
    assert sorted(results) == list(range(50))
```
