"""
Subprocess wrapper for `claude -p` CLI calls.

All LLM calls in the benchmark go through here so rate-limiting,
retry logic, cost tracking, and error logging are centralised.
"""
from __future__ import annotations

import datetime
import json
import os
import subprocess
import time

from benchmark.config import (
    CLI_DELAY_SECONDS,
    CLI_MAX_RETRIES,
    CLI_MODEL,
    CLI_TIMEOUT_SECONDS,
    RESULTS_DIR,
)

# Haiku pricing (USD per 1M tokens, as of 2025)
HAIKU_INPUT_COST_PER_M = 0.80
HAIKU_OUTPUT_COST_PER_M = 4.00

_total_cost_usd: float = 0.0   # session accumulator


def is_cli_available() -> bool:
    """Return True if the `claude` CLI binary is reachable."""
    try:
        subprocess.run(["claude", "--version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def call_claude(prompt: str, *, model: str | None = None) -> dict:
    """
    Call ``claude -p <prompt> --model <model> --output-format json``.

    Returns a dict::

        {
            "output":            str,    # Claude's response text
            "tokens_estimated":  int,    # rough token count
            "cost_usd":          float,  # from CLI JSON (0 if unavailable)
            "error":             str|None
        }

    Retries up to CLI_MAX_RETRIES with exponential backoff on failures.
    Errors are appended to results/cli_errors.log.
    """
    global _total_cost_usd
    model = model or CLI_MODEL
    cmd = [
        "claude", "-p", prompt,
        "--model", model,
        "--output-format", "json",
    ]

    for attempt in range(CLI_MAX_RETRIES):
        # Delay: no sleep on first attempt; exponential backoff on retries only
        delay = 0 if attempt == 0 else min(CLI_DELAY_SECONDS * (2 ** (attempt - 1)), 60)
        time.sleep(delay)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=CLI_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            _log_error(f"Timeout {CLI_TIMEOUT_SECONDS}s attempt={attempt} model={model}")
            continue

        if proc.returncode == 0:
            # Parse JSON envelope from CLI
            try:
                data = json.loads(proc.stdout)
            except json.JSONDecodeError:
                data = {"result": proc.stdout.strip(), "cost_usd": 0}

            output = data.get("result", "")
            cost = float(data.get("cost_usd") or 0)
            _total_cost_usd += cost
            tokens = _estimate_tokens(prompt, output, cost)
            return {
                "output": output,
                "tokens_estimated": tokens,
                "cost_usd": cost,
                "error": None,
            }

        # Non-zero exit — log and decide whether to retry
        stderr = (proc.stderr or "").strip()[:400]
        _log_error(f"exit={proc.returncode} attempt={attempt} model={model}: {stderr}")

        # Retry on rate-limit signals or transient exit codes 1/2
        if "rate limit" in stderr.lower() or proc.returncode in (1, 2):
            continue

        # Non-retriable (auth error, unknown model, etc.)
        return {"output": "", "tokens_estimated": 0, "cost_usd": 0.0, "error": stderr}

    return {
        "output": "",
        "tokens_estimated": 0,
        "cost_usd": 0.0,
        "error": f"Failed after {CLI_MAX_RETRIES} retries",
    }


def total_cost() -> float:
    """Return cumulative cost_usd across all calls this session."""
    return _total_cost_usd


# ── Internal helpers ───────────────────────────────────────────────────────


def _estimate_tokens(prompt: str, output: str, cost_usd: float) -> int:
    """
    Estimate total tokens from cost_usd if available, else from word count.
    Haiku: $0.80/M input + $4.00/M output → avg ~$1.50/M for mixed.
    """
    if cost_usd > 0:
        avg_cost_per_token = 1.50 / 1_000_000
        return max(1, int(cost_usd / avg_cost_per_token))
    # Fallback: words × 1.3 (rough tokenisation ratio)
    return int((len(prompt.split()) + len(output.split())) * 1.3)


def _log_error(msg: str) -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    log_path = os.path.join(RESULTS_DIR, "cli_errors.log")
    ts = datetime.datetime.utcnow().isoformat(timespec="seconds")
    with open(log_path, "a") as f:
        f.write(f"[{ts}] {msg}\n")
