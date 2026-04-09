"""
AttractorFlow condition executor.

Uses the attractor-orchestrator pattern:
- Single-pass multi-step Claude agent via `claude` CLI subprocess
- AttractorFlow MCP modules imported directly (no subprocess needed)
- Regime checked every AF_CHECK_EVERY_N_STEPS; interventions injected into context
"""
from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

from benchmark import cli_runner
from benchmark.config import (
    AF_BUFFER_CAPACITY,
    AF_CHECK_EVERY_N_STEPS,
    AF_WINDOW,
    ATTRACTORFLOW_MCP_PATH,
    ATTRACTORFLOW_SITE_PACKAGES,
)

# ── Import AttractorFlow modules directly ──────────────────────────────────
# Inject AF uv environment's site-packages so sentence_transformers is found
if ATTRACTORFLOW_SITE_PACKAGES not in sys.path:
    sys.path.insert(0, ATTRACTORFLOW_SITE_PACKAGES)
if ATTRACTORFLOW_MCP_PATH not in sys.path:
    sys.path.insert(0, ATTRACTORFLOW_MCP_PATH)

# Disable persistence to avoid cross-trial state contamination
os.environ.setdefault("ATTRACTORFLOW_DISABLE_PERSISTENCE", "1")

from phase_space import PhaseSpaceMonitor        # type: ignore[import]
from lyapunov import LyapunovEstimator           # type: ignore[import]
from classifier import AttractorClassifier       # type: ignore[import]
from bifurcation import BifurcationDetector      # type: ignore[import]


ATTRACTOR_SYSTEM = """\
You are an attractor-engineered orchestration agent.
Work through the task step by step. After each major sub-step, summarize what you just did
in 1-2 sentences (this feeds the trajectory monitor).
Pay close attention to any [GUIDANCE] prepended to your context — it reflects your trajectory health.

CRITICAL RULES:
- TEXT-ONLY response mode. Do NOT use any tools. Do NOT invoke Read, Write, Bash, or any other tool.
- Do NOT create files. Output all code inside ```python code blocks in your text response.
- Work entirely in your text response — the harness extracts your code automatically.

When the task is complete, state clearly: "TASK COMPLETE: <summary of deliverable>"
"""


@dataclass
class AttractorResult:
    output: str
    steps: int = 0
    tokens_used: int = 0
    elapsed_seconds: float = 0.0
    regime_log: list[dict] = field(default_factory=list)   # [{step, regime, lambda}]
    interventions: list[str] = field(default_factory=list)  # intervention hints applied
    final_regime: str = "UNKNOWN"
    final_lambda: float = 0.0


def run(task_prompt: str, goal_text: Optional[str] = None) -> AttractorResult:
    """
    Execute AttractorFlow-orchestrated single-pass agent.
    """
    result = AttractorResult(output="")
    t0 = time.time()

    # ── Initialise AttractorFlow monitors ─────────────────────────────────
    monitor = PhaseSpaceMonitor(capacity=AF_BUFFER_CAPACITY)
    lyapunov_est = LyapunovEstimator(window=AF_WINDOW)
    classifier = AttractorClassifier()

    goal = goal_text or task_prompt[:200]
    monitor.set_goal(goal)        # anchor the trajectory
    monitor.record(task_prompt)   # step 0: initial state

    messages: list[dict] = []
    guidance = ""
    step = 0

    # ── Multi-step agent loop ─────────────────────────────────────────────
    for step in range(20):   # hard cap: 20 sub-steps max
        user_content = ""
        if guidance:
            user_content += f"[GUIDANCE]\n{guidance}\n\n"
        if step == 0:
            user_content += task_prompt
        else:
            user_content += "Continue working on the task. What is your next step?"

        messages.append({"role": "user", "content": user_content})

        # Encode full conversation history into a single CLI prompt
        full_prompt = ATTRACTOR_SYSTEM + "\n\n"
        if len(messages) > 1:
            full_prompt += _msgs_to_str(messages[:-1]) + "\n\n"
        full_prompt += f"[NEW MESSAGE]\n{user_content}"

        cli_result = cli_runner.call_claude(full_prompt)

        if cli_result["error"]:
            result.output += f"\n\n[ERROR step {step + 1}: {cli_result['error']}]"
            break

        assistant_text = cli_result["output"]
        result.tokens_used += cli_result["tokens_estimated"]
        messages.append({"role": "assistant", "content": assistant_text})
        result.output += f"\n\n[Step {step + 1}]\n{assistant_text}"

        # Record state in AttractorFlow
        monitor.record(assistant_text)

        # Check for completion
        if _is_complete(assistant_text):
            result.steps = step + 1
            break

        # Regime check every N steps
        if (step + 1) % AF_CHECK_EVERY_N_STEPS == 0:
            guidance = _get_guidance(monitor, lyapunov_est, classifier, result, step)
        else:
            guidance = ""

    result.steps = step + 1
    result.elapsed_seconds = time.time() - t0

    # Final regime
    if monitor.buffer_size >= 2:
        distances = monitor.get_distance_series()
        emb_matrix = monitor.get_embeddings_matrix()
        stats = monitor.get_stats()
        lya = lyapunov_est.compute(distances, embeddings_matrix=emb_matrix)
        classification = classifier.classify(lya, stats)
        result.final_regime = classification.regime.value
        result.final_lambda = float(lya.ftle)

    return result


def _get_guidance(monitor, lyapunov_est, classifier, result, step: int) -> str:
    """Compute AF regime and return the prescribed intervention hint."""
    if monitor.buffer_size < 3:
        return ""
    distances = monitor.get_distance_series()
    emb_matrix = monitor.get_embeddings_matrix()
    stats = monitor.get_stats()
    lya = lyapunov_est.compute(distances, embeddings_matrix=emb_matrix)
    classification = classifier.classify(lya, stats)

    regime = classification.regime.value
    lam = float(lya.ftle)

    result.regime_log.append({"step": step, "regime": regime, "lambda": round(lam, 4)})

    hint = classification.intervention_hint
    if regime in ("STUCK", "DIVERGING", "OSCILLATING"):
        result.interventions.append(f"step={step} regime={regime}")

    return hint


def _is_complete(text: str) -> bool:
    low = text.lower()
    return "task complete" in low or "<promise>" in low


def _msgs_to_str(messages: list[dict]) -> str:
    """Flatten messages list into labeled text for the stateless CLI prompt."""
    parts = []
    for m in messages:
        parts.append(f"[{m['role'].upper()}]\n{m['content']}")
    return "\n\n".join(parts)
