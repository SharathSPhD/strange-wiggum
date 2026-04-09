"""
Ralph + AttractorFlow combined condition executor.

Ralph loop with AttractorFlow monitoring at each iteration boundary:
- AttractorFlow records Ralph's output after each iteration
- Regime checked every iteration; intervention hint prepended to next Ralph prompt
- Ralph's blind persistence + AttractorFlow's dynamic steering
"""
from __future__ import annotations

import os
import re
import sys
import time
from dataclasses import dataclass, field

from benchmark import cli_runner
from benchmark.config import (
    AF_BUFFER_CAPACITY,
    AF_WINDOW,
    ATTRACTORFLOW_MCP_PATH,
    ATTRACTORFLOW_SITE_PACKAGES,
    COMPLETION_PROMISE,
    MAX_ITERATIONS_RALPH,
)
from benchmark.conditions.attractor import _is_complete, _msgs_to_str, _get_guidance

if ATTRACTORFLOW_SITE_PACKAGES not in sys.path:
    sys.path.insert(0, ATTRACTORFLOW_SITE_PACKAGES)
if ATTRACTORFLOW_MCP_PATH not in sys.path:
    sys.path.insert(0, ATTRACTORFLOW_MCP_PATH)

os.environ.setdefault("ATTRACTORFLOW_DISABLE_PERSISTENCE", "1")

from phase_space import PhaseSpaceMonitor      # type: ignore[import]
from lyapunov import LyapunovEstimator         # type: ignore[import]
from classifier import AttractorClassifier     # type: ignore[import]


STOP_PATTERN = re.compile(
    r"<promise>\s*" + re.escape(COMPLETION_PROMISE) + r"\s*</promise>",
    re.IGNORECASE,
)

COMBINED_SYSTEM = """\
You are an iterative agent operating in a Ralph Wiggum loop enhanced with
AttractorFlow trajectory monitoring. You receive the same task each iteration.
Your previous work accumulates in the conversation history.

Any [ATTRACTOR GUIDANCE] prepended to your prompt reflects your trajectory health — follow it.

CRITICAL RULES:
- TEXT-ONLY response mode. Do NOT use any tools. Do NOT invoke Read, Write, Bash, or any other tool.
- Do NOT create files. Output all code inside ```python code blocks in your text response.
- Work entirely in your text response — the harness extracts your code automatically.

When the task is fully complete, output exactly:
<promise>TASK COMPLETE</promise>
"""


@dataclass
class CombinedResult:
    output: str
    iterations: int = 0
    tokens_used: int = 0
    elapsed_seconds: float = 0.0
    completion_detected: bool = False
    regime_log: list[dict] = field(default_factory=list)
    interventions: list[str] = field(default_factory=list)
    iteration_outputs: list[str] = field(default_factory=list)


def run(task_prompt: str) -> CombinedResult:
    """
    Execute Ralph loop with per-iteration AttractorFlow monitoring.
    """
    result = CombinedResult(output="")
    t0 = time.time()

    # Initialise AttractorFlow
    monitor = PhaseSpaceMonitor(capacity=AF_BUFFER_CAPACITY)
    lyapunov_est = LyapunovEstimator(window=AF_WINDOW)
    classifier = AttractorClassifier()

    monitor.set_goal(task_prompt[:200])
    monitor.record(task_prompt)

    messages: list[dict] = []
    guidance = ""

    for i in range(MAX_ITERATIONS_RALPH):
        result.iterations = i + 1

        # Build prompt with optional AttractorFlow guidance
        user_content = f"[Iteration {i + 1}]\n\n"
        if guidance:
            user_content += f"[ATTRACTOR GUIDANCE]\n{guidance}\n\n"
        user_content += task_prompt

        # Encode full conversation history into a single CLI prompt
        full_prompt = COMBINED_SYSTEM + "\n\n"
        if messages:
            full_prompt += _msgs_to_str(messages) + "\n\n"
        full_prompt += f"[NEW MESSAGE]\n{user_content}"

        messages.append({"role": "user", "content": user_content})

        cli_result = cli_runner.call_claude(full_prompt)

        if cli_result["error"]:
            result.iteration_outputs.append(f"[ERROR: {cli_result['error']}]")
            break

        assistant_text = cli_result["output"]
        result.tokens_used += cli_result["tokens_estimated"]
        result.iteration_outputs.append(assistant_text)
        messages.append({"role": "assistant", "content": assistant_text})

        # Record in AttractorFlow after each Ralph iteration
        monitor.record(assistant_text)

        # Check Ralph completion
        if _is_complete(assistant_text) or STOP_PATTERN.search(assistant_text):
            result.completion_detected = True
            break

        # Get AttractorFlow guidance for next iteration
        guidance = _get_guidance(monitor, lyapunov_est, classifier, result, i)

    result.output = "\n\n---\n\n".join(result.iteration_outputs)
    result.elapsed_seconds = time.time() - t0
    return result
