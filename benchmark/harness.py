"""
Benchmark harness.

Orchestrates all 135 trials (15 tasks × 3 conditions × 3 reps) with:
- Latin-square condition ordering per rep
- Blinded output file naming (uuid, no condition label)
- Automatic test execution for coding tasks
- Score collection via LLM judge
- Incremental CSV writes (resumable on crash)

Usage:
    python -m benchmark.harness                             # full run
    python -m benchmark.harness --dry-run                  # validate only
    python -m benchmark.harness --tasks C01 --conditions ralph --reps 1
    python -m benchmark.harness --tasks C01,A01 --reps 2
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from benchmark.config import (
    BENCHMARK_DIR,
    BLIND_MANIFEST,
    LATIN_SQUARE,
    RAW_DIR,
    SCORES_CSV,
    TASKS_DIR,
    TEST_PASS_BONUS,
)
from benchmark.judge import judge


# ── Task registry ─────────────────────────────────────────────────────────

def load_tasks(task_ids: Optional[list[str]] = None) -> dict[str, dict]:
    """Load task specs from markdown files. Returns {task_id: {spec, category, test_file}}."""
    tasks = {}
    for category in ("coding", "analysis"):
        task_dir = Path(TASKS_DIR) / category
        for md_file in sorted(task_dir.glob("*.md")):
            tid = md_file.stem.split("_")[0]  # e.g. "C01" from "C01_binary_search_tree"
            if task_ids and tid not in task_ids:
                continue
            spec = md_file.read_text()
            # Extract test suite block (coding only)
            test_code = _extract_test_code(spec) if category == "coding" else None
            tasks[tid] = {
                "spec": spec,
                "category": category,
                "test_code": test_code,
                "file": str(md_file),
            }
    return tasks


def _extract_test_code(spec: str) -> Optional[str]:
    """Extract ```python ... ``` block containing pytest suite from task markdown."""
    import re
    matches = re.findall(r"```python\n(.*?)```", spec, re.DOTALL)
    # Return the block that starts with '# test_'
    for block in matches:
        if block.strip().startswith("# test_"):
            return block
    return None


# ── Trial execution ────────────────────────────────────────────────────────

@dataclass
class TrialResult:
    task_id: str
    condition: str
    rep: int
    uuid: str
    quality_score: int
    iterations: int
    tokens: int
    elapsed: float
    completion: bool
    af_interventions: int
    final_regime: str
    final_lambda: float
    test_passed: Optional[bool]
    judge_rationale: str


def run_trial(task_id: str, task: dict, condition: str, rep: int, dry_run: bool = False) -> TrialResult:
    trial_uuid = str(uuid.uuid4())[:8]
    print(f"  [{task_id}] {condition} rep={rep} uuid={trial_uuid}", end="", flush=True)

    if dry_run:
        print(" [DRY RUN]")
        return _dummy_result(task_id, condition, rep, trial_uuid)

    # ── Execute condition ──────────────────────────────────────────────────
    if condition == "ralph":
        from benchmark.conditions import ralph
        result = ralph.run(task["spec"])
        output = result.output
        iterations = result.iterations
        tokens = result.tokens_used
        elapsed = result.elapsed_seconds
        completion = result.completion_detected
        af_interventions = 0
        final_regime = "N/A"
        final_lambda = 0.0

    elif condition == "attractor":
        from benchmark.conditions import attractor
        result = attractor.run(task["spec"])
        output = result.output
        iterations = result.steps
        tokens = result.tokens_used
        elapsed = result.elapsed_seconds
        completion = True  # single-pass always "completes"
        af_interventions = len(result.interventions)
        final_regime = result.final_regime
        final_lambda = result.final_lambda

    elif condition == "combined":
        from benchmark.conditions import combined
        result = combined.run(task["spec"])
        output = result.output
        iterations = result.iterations
        tokens = result.tokens_used
        elapsed = result.elapsed_seconds
        completion = result.completion_detected
        af_interventions = len(result.interventions)
        final_regime = result.regime_log[-1]["regime"] if result.regime_log else "N/A"
        final_lambda = result.regime_log[-1]["lambda"] if result.regime_log else 0.0

    else:
        raise ValueError(f"Unknown condition: {condition}")

    # ── Save blinded output ────────────────────────────────────────────────
    out_path = os.path.join(RAW_DIR, f"{trial_uuid}.txt")
    Path(out_path).write_text(output)

    # ── Update blind manifest ──────────────────────────────────────────────
    _update_manifest(trial_uuid, task_id, condition, rep)

    # ── Run tests (coding tasks) ───────────────────────────────────────────
    test_passed = None
    if task["category"] == "coding" and task["test_code"]:
        test_passed = _run_tests(task["test_code"], output)

    # ── Judge output ───────────────────────────────────────────────────────
    judgment = judge.score(task["spec"], output)
    base_score = judgment["score"]

    # Apply test pass bonus (capped at 10)
    if test_passed is True:
        quality_score = min(10, base_score + TEST_PASS_BONUS)
    else:
        quality_score = base_score

    print(f" → score={quality_score} iters={iterations} {'✓' if completion else '✗'}")

    return TrialResult(
        task_id=task_id,
        condition=condition,
        rep=rep,
        uuid=trial_uuid,
        quality_score=quality_score,
        iterations=iterations,
        tokens=tokens,
        elapsed=round(elapsed, 2),
        completion=completion,
        af_interventions=af_interventions,
        final_regime=final_regime,
        final_lambda=round(final_lambda, 4),
        test_passed=test_passed,
        judge_rationale=judgment.get("rationale", ""),
    )


def _run_tests(test_code: str, solution_output: str) -> bool:
    """Extract solution.py from output, write to temp dir, run pytest."""
    import re
    # Extract ```python ... ``` block from output (the solution)
    matches = re.findall(r"```python\n(.*?)```", solution_output, re.DOTALL)
    solution_code = matches[0] if matches else solution_output

    with tempfile.TemporaryDirectory() as tmpdir:
        sol_path = os.path.join(tmpdir, "solution.py")
        test_path = os.path.join(tmpdir, "test_solution.py")
        Path(sol_path).write_text(solution_code)
        Path(test_path).write_text(test_code)

        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", test_path, "-x", "-q", "--tb=no"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return proc.returncode == 0
        except subprocess.TimeoutExpired:
            return False


def _update_manifest(trial_uuid: str, task_id: str, condition: str, rep: int):
    manifest = {}
    if os.path.exists(BLIND_MANIFEST):
        with open(BLIND_MANIFEST) as f:
            manifest = json.load(f)
    manifest[trial_uuid] = {"task_id": task_id, "condition": condition, "rep": rep}
    with open(BLIND_MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)


def _dummy_result(task_id, condition, rep, trial_uuid) -> TrialResult:
    return TrialResult(task_id=task_id, condition=condition, rep=rep, uuid=trial_uuid,
                       quality_score=0, iterations=0, tokens=0, elapsed=0.0,
                       completion=False, af_interventions=0, final_regime="N/A",
                       final_lambda=0.0, test_passed=None, judge_rationale="dry-run")


# ── CSV writer ─────────────────────────────────────────────────────────────

FIELDNAMES = [
    "task_id", "condition", "rep", "uuid", "quality_score", "iterations",
    "tokens", "elapsed", "completion", "af_interventions",
    "final_regime", "final_lambda", "test_passed", "judge_rationale",
]


def append_result(trial: TrialResult):
    exists = os.path.exists(SCORES_CSV)
    with open(SCORES_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not exists:
            writer.writeheader()
        writer.writerow(asdict(trial))


def already_run(task_id: str, condition: str, rep: int) -> bool:
    if not os.path.exists(SCORES_CSV):
        return False
    with open(SCORES_CSV) as f:
        for row in csv.DictReader(f):
            if row["task_id"] == task_id and row["condition"] == condition and row["rep"] == str(rep):
                return True
    return False


# ── Main orchestrator ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ralph vs AttractorFlow Benchmark")
    parser.add_argument("--dry-run", action="store_true", help="Validate without API calls")
    parser.add_argument("--tasks", default=None, help="Comma-separated task IDs, e.g. C01,A01")
    parser.add_argument("--conditions", default=None, help="Comma-separated: ralph,attractor,combined")
    parser.add_argument("--reps", type=int, default=3, help="Number of reps (default 3)")
    args = parser.parse_args()

    task_ids = [t.strip() for t in args.tasks.split(",")] if args.tasks else None
    condition_filter = [c.strip() for c in args.conditions.split(",")] if args.conditions else None

    # Validate CLI is available before any trials run
    if not args.dry_run:
        from benchmark import cli_runner as _cr
        if not _cr.is_cli_available():
            print("ERROR: 'claude' CLI not found. Install Claude Code first.")
            sys.exit(1)

        # Validate test runner dependencies
        def _check_test_deps():
            try:
                import pytest  # noqa: F401
                import pytest_asyncio  # noqa: F401
            except ImportError as e:
                print(f"ERROR: Missing test dependency: {e}")
                print("Run: pip install pytest pytest-asyncio aiohttp")
                sys.exit(1)
        _check_test_deps()

        # Pre-load AF embedding model so trial timing is unaffected
        def _warmup_af():
            try:
                from benchmark.config import ATTRACTORFLOW_SITE_PACKAGES, ATTRACTORFLOW_MCP_PATH
                if ATTRACTORFLOW_SITE_PACKAGES not in sys.path:
                    sys.path.insert(0, ATTRACTORFLOW_SITE_PACKAGES)
                if ATTRACTORFLOW_MCP_PATH not in sys.path:
                    sys.path.insert(0, ATTRACTORFLOW_MCP_PATH)
                from phase_space import PhaseSpaceMonitor  # noqa: F401
                m = PhaseSpaceMonitor(capacity=3)
                m.record("warmup")
                print("AttractorFlow embedding model warmed up.")
            except Exception as e:
                print(f"[WARN] AF warmup failed: {e} — continuing anyway")
        _warmup_af()

    tasks = load_tasks(task_ids)
    if not tasks:
        print("ERROR: No tasks found."); sys.exit(1)

    os.makedirs(RAW_DIR, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Benchmark: {len(tasks)} tasks × {args.reps} reps × 3 conditions")
    print(f"Total trials: {len(tasks) * args.reps * 3}")
    print(f"{'='*60}\n")

    total = 0
    for task_id, task in tasks.items():
        print(f"\nTask {task_id} ({task['category']}):")
        for rep in range(args.reps):
            order = LATIN_SQUARE[rep % 3]   # Latin square condition order
            for condition in order:
                if condition_filter and condition not in condition_filter:
                    continue
                if already_run(task_id, condition, rep) and not args.dry_run:
                    print(f"  [{task_id}] {condition} rep={rep} [SKIPPED — already in CSV]")
                    continue
                trial = run_trial(task_id, task, condition, rep, dry_run=args.dry_run)
                if not args.dry_run:
                    append_result(trial)
                total += 1

    print(f"\n{'='*60}")
    print(f"Done. {total} trials {'validated' if args.dry_run else 'completed'}.")
    if not args.dry_run:
        from benchmark import cli_runner as _cr
        print(f"Results: {SCORES_CSV}")
        print(f"Estimated total cost: ${_cr.total_cost():.4f} USD")
        print(f"Next: python -m benchmark.stats && python -m benchmark.report")


if __name__ == "__main__":
    main()
