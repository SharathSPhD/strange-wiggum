"""
agent_harness.py — Trial preparation and finalization for the attractor condition.

The attractor condition uses the AttractorFlow plugin correctly:
  - attractor-orchestrator Agent (spawned via Claude Code's Agent tool)
  - MCP tools: attractorflow_record_state, get_regime, get_lyapunov, etc.
  - File tools: Write, Bash (for writing and testing solution.py)
  - Subagent spawning: explorer-agent / convergence-agent as needed

Since the Agent tool is only available inside a Claude Code session, this module
provides prepare/finalize helpers that bracket the agent spawn:

  1. prepare_attractor_trial(task_id, rep)
       → returns {trial_uuid, temp_dir, agent_prompt}

  2. [Caller spawns attractor-orchestrator Agent with agent_prompt]

  3. finalize_attractor_trial(task_id, rep, trial_uuid, agent_text, temp_dir, elapsed, ...)
       → runs pytest on solution.py, judges output, writes scores.csv row
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from benchmark.config import (
    BLIND_MANIFEST,
    RAW_DIR,
    RESULTS_DIR,
    SCORES_CSV,
    TEST_PASS_BONUS,
)

FIELDNAMES = [
    "task_id", "condition", "rep", "uuid", "quality_score",
    "iterations", "tokens", "elapsed", "completion",
    "af_interventions", "final_regime", "final_lambda",
    "test_passed", "judge_rationale",
]


def prepare_attractor_trial(task_id: str, rep: int) -> dict:
    """
    Set up the working environment for an attractor trial.

    Writes the test suite to a persistent temp directory and builds the
    agent prompt that instructs the attractor-orchestrator how to work.

    Returns:
        trial_uuid   — 8-char hex ID (assign before spawning agent)
        temp_dir     — absolute path (persists until finalize_attractor_trial cleans it)
        agent_prompt — full prompt string to pass to attractor-orchestrator Agent
        task_spec    — raw task spec (for reference)
        test_code    — pytest suite code (for reference)
    """
    from benchmark.harness import load_tasks, _extract_test_code

    tasks = load_tasks([task_id])
    if task_id not in tasks:
        raise ValueError(f"Task {task_id!r} not found in tasks directory")

    task = tasks[task_id]
    task_spec: str = task["spec"]
    test_code: Optional[str] = task.get("test_code") or _extract_test_code(task_spec)

    trial_uuid = str(uuid.uuid4())[:8]

    # Persistent temp dir — NOT auto-cleaned; finalize() removes it
    temp_dir = tempfile.mkdtemp(prefix=f"attractor_{task_id}_{trial_uuid}_")

    # Write test suite so agent can validate with Bash
    if test_code:
        Path(os.path.join(temp_dir, "test_solution.py")).write_text(test_code)

    # Build agent prompt for attractor-orchestrator
    agent_prompt = _build_agent_prompt(task_spec, temp_dir)

    # Persist trial metadata so finalize() can work without re-passing everything
    meta = {
        "task_id": task_id,
        "rep": rep,
        "trial_uuid": trial_uuid,
        "task_spec": task_spec,
        "test_code": test_code or "",
    }
    Path(os.path.join(temp_dir, "_trial_meta.json")).write_text(json.dumps(meta, indent=2))

    print(f"[agent_harness] Trial prepared: {task_id}/attractor/rep={rep}  uuid={trial_uuid}")
    print(f"[agent_harness] Working directory: {temp_dir}")

    return {
        "trial_uuid": trial_uuid,
        "temp_dir": temp_dir,
        "agent_prompt": agent_prompt,
        "task_spec": task_spec,
        "test_code": test_code or "",
    }


def _build_agent_prompt(task_spec: str, temp_dir: str) -> str:
    """
    Build the prompt for the attractor-orchestrator Agent.

    The orchestrator will:
    - Use AF MCP tools to monitor its trajectory
    - Write solution.py to temp_dir
    - Run the pre-written test suite via Bash
    - Spawn explorer/convergence subagents as the regime requires
    """
    return f"""\
You are the attractor-orchestrator for a benchmark coding evaluation trial.

WORKING DIRECTORY: {temp_dir}

━━━ TASK SPECIFICATION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{task_spec}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ATTRACTOR ORCHESTRATION INSTRUCTIONS:

1. USE AttractorFlow MCP tools throughout:
   - Call attractorflow_record_state(text) after EVERY meaningful step
     (after planning, after writing code, after running tests, etc.)
   - Call attractorflow_get_regime() every 2-3 steps to check trajectory health
   - Call attractorflow_get_lyapunov() to get the current FTLE value (λ)
   - If regime is STUCK or DIVERGING → spawn explorer-agent to find alternatives
   - If regime is CONVERGING → spawn convergence-agent to drive to completion
   - Call attractorflow_checkpoint() when you reach a verified-good state

2. WRITE the final solution to: {temp_dir}/solution.py
   - The Write tool creates/overwrites the file directly
   - Do NOT just print code in text; actually write the file

3. RUN tests to verify before declaring complete:
   Bash: cd {temp_dir} && python -m pytest test_solution.py -v --tb=short
   - The test suite is already at {temp_dir}/test_solution.py
   - Only declare TASK COMPLETE after ALL tests pass

4. When done, output:
   a) The COMPLETE final solution as a ```python code block
   b) Then the structured summary:

   TASK COMPLETE: <one-line description of what was implemented>
   AF Summary:
   - Steps taken: N
   - Regimes observed: [list]
   - Interventions: N
   - Final λ: <value>
   - Tests passed: Yes/No
"""


def finalize_attractor_trial(
    task_id: str,
    rep: int,
    trial_uuid: str,
    agent_text_output: str,
    temp_dir: str,
    elapsed_seconds: float,
    af_interventions: int = 0,
    final_regime: str = "UNKNOWN",
    final_lambda: float = 0.0,
    iterations: int = 1,
) -> dict:
    """
    After the attractor-orchestrator Agent returns, finalize the trial:

    1. Read solution.py from temp_dir (written by agent with Write tool)
    2. Run pytest against solution.py
    3. Judge the full agent text output
    4. Write row to scores.csv
    5. Save blinded output to results/raw/<uuid>.txt
    6. Update blind manifest
    7. Clean up temp_dir

    Returns the row dict written to CSV.
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)

    # ── 1. Get solution code ───────────────────────────────────────────────
    solution_file = os.path.join(temp_dir, "solution.py")
    if os.path.exists(solution_file):
        solution_code = Path(solution_file).read_text()
        print(f"[agent_harness] solution.py found ({len(solution_code)} chars)")
    else:
        # Fallback: extract ```python block from agent text
        matches = re.findall(r"```python\n(.*?)```", agent_text_output, re.DOTALL)
        solution_code = matches[0] if matches else ""
        print("[agent_harness] WARN: solution.py not in temp dir — extracted from agent text")
        if solution_code:
            Path(solution_file).write_text(solution_code)

    # ── 2. Run pytest ──────────────────────────────────────────────────────
    test_passed: Optional[bool] = None
    test_file = os.path.join(temp_dir, "test_solution.py")
    if os.path.exists(test_file) and solution_code:
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "test_solution.py", "-x", "-q", "--tb=short",
                 "--asyncio-mode=auto"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            test_passed = proc.returncode == 0
            status = "PASS" if test_passed else "FAIL"
            print(f"[agent_harness] pytest: {status}")
            if not test_passed:
                print(proc.stdout[-800:])
        except subprocess.TimeoutExpired:
            test_passed = False
            print("[agent_harness] pytest timed out")

    # ── 3. Load task spec for judging ─────────────────────────────────────
    task_spec = ""
    meta_path = os.path.join(temp_dir, "_trial_meta.json")
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            task_spec = json.load(f).get("task_spec", "")

    # ── 4. Judge output ───────────────────────────────────────────────────
    # Include solution code in submission so judge sees actual implementation
    judge_submission = agent_text_output
    if solution_code and "```python" not in agent_text_output:
        judge_submission = (
            f"{agent_text_output}\n\n"
            f"--- SOLUTION CODE ---\n```python\n{solution_code}\n```"
        )

    from benchmark.judge import judge
    judgment = judge.score(task_spec, judge_submission)
    base_score = judgment.get("score", 0)
    quality_score = min(10, base_score + TEST_PASS_BONUS) if test_passed else base_score
    print(f"[agent_harness] Judge: base={base_score} bonus={TEST_PASS_BONUS if test_passed else 0} → final={quality_score}")

    # ── 5. Save blinded output ─────────────────────────────────────────────
    out_path = os.path.join(RAW_DIR, f"{trial_uuid}.txt")
    Path(out_path).write_text(agent_text_output)

    # ── 6. Update blind manifest ───────────────────────────────────────────
    manifest: dict = {}
    if os.path.exists(BLIND_MANIFEST):
        with open(BLIND_MANIFEST) as f:
            manifest = json.load(f)
    manifest[trial_uuid] = {"task_id": task_id, "condition": "attractor", "rep": rep}
    with open(BLIND_MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)

    # ── 7. Write CSV row ───────────────────────────────────────────────────
    token_estimate = len(agent_text_output.split())  # word count proxy
    write_header = not os.path.exists(SCORES_CSV)
    row = {
        "task_id": task_id,
        "condition": "attractor",
        "rep": rep,
        "uuid": trial_uuid,
        "quality_score": quality_score,
        "iterations": iterations,
        "tokens": token_estimate,
        "elapsed": round(elapsed_seconds, 2),
        "completion": True,
        "af_interventions": af_interventions,
        "final_regime": final_regime,
        "final_lambda": round(final_lambda, 4),
        "test_passed": test_passed,
        "judge_rationale": judgment.get("rationale", ""),
    }
    with open(SCORES_CSV, "a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(row)
    print(f"[agent_harness] Row written → {SCORES_CSV}")

    # ── 8. Clean up temp dir ──────────────────────────────────────────────
    shutil.rmtree(temp_dir, ignore_errors=True)

    print(f"\n{'='*60}")
    print(f"RESULT: {task_id}/attractor/rep={rep}")
    print(f"  score={quality_score}  test={'PASS' if test_passed else 'FAIL'}")
    print(f"  regime={final_regime}  λ={final_lambda:.4f}")
    print(f"  interventions={af_interventions}  iterations={iterations}")
    print(f"{'='*60}")

    return row
