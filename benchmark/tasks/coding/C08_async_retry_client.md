# C08 — Async HTTP Client with Retry + Exponential Backoff

## Task

Implement an async `fetch_with_retry` function:

```python
async def fetch_with_retry(
    url: str,
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
    retryable_status: tuple[int, ...] = (429, 500, 502, 503, 504),
) -> dict:
    """
    Fetch a URL with exponential backoff retry.
    Returns {"status": int, "body": str, "attempts": int}.
    Raises RuntimeError if all retries exhausted.
    """
```

Requirements:
- Exponential backoff: delay = min(base_delay * 2^attempt, max_delay)
- Jitter: when True, multiply delay by random.uniform(0.5, 1.5)
- Only retry on `retryable_status` codes (not 4xx other than 429)
- Raise `RuntimeError("Max retries exceeded")` when all retries fail
- Use `aiohttp` for HTTP (mock it in tests)
- `attempts` in return value = total attempts made (including the one that succeeded)

Output your COMPLETE solution as a single ```python code block in your TEXT RESPONSE (do not use any file tools). When complete: <promise>TASK COMPLETE</promise>

## Test Suite (pytest)

```python
# test_C08.py
import asyncio, pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

def make_response(status, body="ok"):
    resp = AsyncMock()
    resp.status = status
    resp.text = AsyncMock(return_value=body)
    return resp

async def test_success_first_try():
    from solution import fetch_with_retry
    with patch("aiohttp.ClientSession") as mock_session:
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=ctx)
        ctx.__aexit__ = AsyncMock(return_value=False)
        ctx.get = AsyncMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=make_response(200)), __aexit__=AsyncMock(return_value=False)))
        mock_session.return_value = ctx
        result = await fetch_with_retry("http://example.com", base_delay=0)
        assert result["status"] == 200
        assert result["attempts"] == 1

async def test_retry_then_success():
    from solution import fetch_with_retry
    responses = [make_response(503), make_response(503), make_response(200)]
    call_count = 0
    async def mock_get(*a, **kw):
        nonlocal call_count
        r = responses[call_count]; call_count += 1
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=r)
        ctx.__aexit__ = AsyncMock(return_value=False)
        return ctx
    with patch("aiohttp.ClientSession") as ms:
        sess = AsyncMock(); sess.__aenter__ = AsyncMock(return_value=sess)
        sess.__aexit__ = AsyncMock(return_value=False); sess.get = mock_get
        ms.return_value = sess
        result = await fetch_with_retry("http://x.com", base_delay=0, jitter=False)
        assert result["status"] == 200 and result["attempts"] == 3

async def test_max_retries_exceeded():
    from solution import fetch_with_retry
    async def always_503(*a, **kw):
        ctx = AsyncMock(); ctx.__aenter__ = AsyncMock(return_value=make_response(503))
        ctx.__aexit__ = AsyncMock(return_value=False); return ctx
    with patch("aiohttp.ClientSession") as ms:
        sess = AsyncMock(); sess.__aenter__ = AsyncMock(return_value=sess)
        sess.__aexit__ = AsyncMock(return_value=False); sess.get = always_503
        ms.return_value = sess
        with pytest.raises(RuntimeError, match="Max retries exceeded"):
            await fetch_with_retry("http://x.com", max_retries=2, base_delay=0)
```
