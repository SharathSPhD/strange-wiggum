"""
Blinded LLM judge.

Reads a uuid-named output file (no condition label) and scores it 0-10
using the rubric. Returns a structured dict suitable for scores.csv.

Uses the `claude` CLI via cli_runner (no SDK key required).
"""
from __future__ import annotations

import json
import os
import re

from benchmark import cli_runner

_RUBRIC_PATH = os.path.join(os.path.dirname(__file__), "rubric.md")
with open(_RUBRIC_PATH) as f:
    RUBRIC = f.read()

_JSON_RE = re.compile(r"\{.*?\}", re.DOTALL)


def score(task_spec: str, submission: str) -> dict:
    """
    Score a blinded submission against its task spec.

    Args:
        task_spec: The original task prompt (from task .md file).
        submission: The raw output produced by one condition.

    Returns:
        dict with keys: score, correctness_score, depth_score,
                        clarity_score, structure_score, rationale
    """
    prompt = f"""{RUBRIC}

---

## TASK SPECIFICATION

{task_spec}

---

## SUBMISSION

{submission}

---

Score this submission against the rubric above.
Return ONLY a valid JSON object with exactly these keys:
  score (integer 0-10), correctness_score (0-10), depth_score (0-10),
  clarity_score (0-10), structure_score (0-10), rationale (string).
No other text. No markdown fences. Just the JSON object.
"""

    cli_result = cli_runner.call_claude(prompt)

    if cli_result["error"]:
        return {
            "score": 0,
            "rationale": f"Judge error: {cli_result['error']}",
            "correctness_score": 0,
            "depth_score": 0,
            "clarity_score": 0,
            "structure_score": 0,
        }

    raw = cli_result["output"].strip()

    # Extract JSON object from response
    m = _JSON_RE.search(raw)
    if not m:
        return {
            "score": 0,
            "rationale": f"Judge parse error: {raw[:200]}",
            "correctness_score": 0,
            "depth_score": 0,
            "clarity_score": 0,
            "structure_score": 0,
        }

    try:
        parsed = json.loads(m.group())
    except json.JSONDecodeError:
        return {
            "score": 0,
            "rationale": "Judge JSON decode error",
            "correctness_score": 0,
            "depth_score": 0,
            "clarity_score": 0,
            "structure_score": 0,
        }

    # Clamp score to valid range
    parsed["score"] = max(0, min(10, int(parsed.get("score", 0))))
    return parsed
