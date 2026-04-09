# C02 — Token Bucket Rate Limiter

## Task

Implement a thread-safe `TokenBucketRateLimiter` class in Python.

Specification:
- `__init__(rate: float, capacity: float)` — `rate` = tokens added per second, `capacity` = max tokens
- `allow(tokens: float = 1.0) -> bool` — consume `tokens` if available; return True if allowed, False if denied
- `available_tokens() -> float` — return current token count (for testing)

Requirements:
- Thread-safe (multiple threads can call `allow()` concurrently)
- Tokens refill continuously over time (not in discrete ticks)
- Never exceed `capacity`
- Use `time.monotonic()` (mockable via dependency injection in tests)

Output your COMPLETE solution as a single ```python code block in your TEXT RESPONSE (do not use any file tools). When complete: <promise>TASK COMPLETE</promise>

## Test Suite (pytest)

```python
# test_C02.py
import time, threading, pytest
from unittest.mock import patch
from solution import TokenBucketRateLimiter

def test_basic_allow():
    rl = TokenBucketRateLimiter(rate=10, capacity=10)
    assert rl.allow(5)
    assert rl.allow(5)
    assert not rl.allow(1)  # bucket empty

def test_refill():
    with patch("time.monotonic", side_effect=[0.0, 0.0, 1.0]):
        rl = TokenBucketRateLimiter(rate=10, capacity=10)
        assert rl.allow(10)          # drain
        assert not rl.allow(1)       # empty at t=0
        assert rl.allow(10)          # refilled at t=1

def test_capacity_cap():
    with patch("time.monotonic", side_effect=[0.0, 100.0]):
        rl = TokenBucketRateLimiter(rate=1, capacity=5)
        _ = rl.available_tokens()    # init at t=0
        assert rl.available_tokens() <= 5   # capped at capacity at t=100

def test_thread_safety():
    rl = TokenBucketRateLimiter(rate=1000, capacity=100)
    results = []
    def worker():
        results.append(rl.allow(1))
    threads = [threading.Thread(target=worker) for _ in range(200)]
    for t in threads: t.start()
    for t in threads: t.join()
    allowed = sum(results)
    assert allowed <= 100   # never over-granted
```
