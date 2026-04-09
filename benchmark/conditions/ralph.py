"""
Ralph condition executor.

Implements Ralph Wiggum loop semantics via the `claude` CLI subprocess:
- Same prompt fed to Claude on every iteration
- Conversation history encoded as formatted text (CLI is stateless)
- Loop terminates on <promise>TASK COMPLETE</promise> or max iterations
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from benchmark import cli_runner
from benchmark.config import (
    COMPLETION_PROMISE,
    MAX_ITERATIONS_RALPH,
)


STOP_PATTERN = re.compile(
    r"<promise>\s*" + re.escape(COMPLETION_PROMISE) + r"\s*</promise>",
    re.IGNORECASE,
)

RALPH_SYSTEM = """\
You are an iterative coding and analysis agent operating in a Ralph Wiggum loop.
On each iteration you receive the same task prompt. Your previous work is accumulated
in the conversation history. Build on it incrementally.

CRITICAL RULES:
- You are in a TEXT-ONLY response mode. Do NOT use any tools. Do NOT invoke Read, Write, Bash, or any other tool.
- Do NOT ask for permission to create files. Do NOT create files. Output code ONLY inside ```python code blocks in your text response.
- The test harness will extract your code from the response automatically.
- Work entirely in your response text.

When the task is fully complete and your solution is in the response, output exactly:
<promise>TASK COMPLETE</promise>

Do NOT output this promise unless the task is genuinely complete.
"""


@dataclass
class RalphResult:
    output: str                        # final combined output
    iterations: int = 0
    tokens_used: int = 0
    completion_detected: bool = False
    elapsed_seconds: float = 0.0
    iteration_outputs: list[str] = field(default_factory=list)


def run(task_prompt: str, *, hint: str = "") -> RalphResult:
    """
    Execute a Ralph loop for the given task prompt.

    Args:
        task_prompt: The task specification (constant across all iterations).
        hint: Optional prepended hint (used by combined condition).

    Returns:
        RalphResult with all metrics.
    """
    messages: list[dict] = []
    result = RalphResult(output="")
    t0 = time.time()

    for i in range(MAX_ITERATIONS_RALPH):
        result.iterations = i + 1

        # Build the user message for this iteration
        user_content = f"[Iteration {i + 1}]\n\n"
        if hint:
            user_content += f"[GUIDANCE FOR THIS ITERATION]\n{hint}\n\n"
        user_content += task_prompt

        # Encode full conversation history into a single prompt
        full_prompt = RALPH_SYSTEM + "\n\n"
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

        # Add assistant turn to history so next iteration sees it
        messages.append({"role": "assistant", "content": assistant_text})

        if STOP_PATTERN.search(assistant_text):
            result.completion_detected = True
            break

    result.output = "\n\n---\n\n".join(result.iteration_outputs)
    result.elapsed_seconds = time.time() - t0
    return result


def _msgs_to_str(messages: list[dict]) -> str:
    """Flatten messages list into labeled text for the stateless CLI prompt."""
    parts = []
    for m in messages:
        parts.append(f"[{m['role'].upper()}]\n{m['content']}")
    return "\n\n".join(parts)
