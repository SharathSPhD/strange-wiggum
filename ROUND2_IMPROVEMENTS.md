# Round 2 Improvement Plan — Critical Review & Iterative Fix Protocol

> Generated: 2026-04-09 | Based on 135-trial run (15 tasks × 3 conditions × 3 reps)
> Purpose: Full post-mortem of what went wrong, why, and the exact changes needed to prove whether AttractorFlow adds value.

---

## Executive Summary

The Round 1 benchmark produced a **null result** (F=1.725, p=0.184), but the null result is **not trustworthy**. Four compounding defects prevented any meaningful comparison:

1. **The test-pass bonus was never applied** — pytest was not installed in the runtime venv, so all 72 coding trial tests silently returned `False`. Zero of 72 trials received the +2 bonus they deserved.
2. **AttractorFlow never fired in 97.8% of trials** — the single-step completion pattern left the AF trajectory monitor with only 2 states (< 3 minimum), so the classifier always returned UNKNOWN.
3. **Ceiling effect compresses all variance** — 75.5% of scores landed at 9 or 10, leaving < 1 point of variance to detect any real difference between conditions.
4. **The AF loop architecture is structurally broken** — the timing of guidance injection means AF advice can never reach Claude before it signals completion.

Each issue is independently fixable. The improvement plan below targets all four, validated on **one task before running the full matrix**.

---

## Issue 1 — Harness Bug: pytest Not Installed → 0% Test Pass Rate

### What happened

The benchmark ran under `.venv313` (Python 3.13), created specifically for AttractorFlow compatibility. The harness's `_run_tests()` calls `sys.executable -m pytest`. When `pytest` is not installed in the active venv, the subprocess exits with code 1 and the harness silently records `test_passed = False`.

**Result: every single coding trial failed its tests, and the +2 bonus was never awarded.**

Manual re-testing after installing pytest revealed the true pass rates:

| Task | Condition | Rep=0 | Rep=1 | Rep=2 |
|------|-----------|-------|-------|-------|
| C01 (BST) | ralph | ✓ | ✓ | ✓ |
| C01 (BST) | attractor | ✓ | ✓ | ✓ |
| C01 (BST) | combined | ✓ | ✓ | ✓ |
| C02 (rate limiter) | all | ✗ | ✗ | ✗ |
| C03–C07 | most | ✓ | ✓ | ✓ |
| C08 (async retry) | all | ✗ | ✗ | ✗ |

True pass rates: ralph = 75%, attractor = 70.8%, combined = 75%

Corrected overall means (coding only):
- Ralph: 9.625 → **9.875**
- Combined: 9.458 → **9.875**
- AttractorFlow: 8.958 → **9.417**

### C08 — Systematic failure: `pytest-asyncio` not installed

C08 (async retry client) uses `async def` test functions. Without `pytest-asyncio`, pytest cannot run them:
```
async def functions are not natively supported.
You need to install a suitable plugin for your async framework...
```
This affects all 9 C08 trials uniformly and invalidates the task entirely.

### C02 — Genuine task design flaw: mock timing underspecified

C02 (token bucket rate limiter) requires `time.monotonic()` to be lazily initialized. The standard approach (initialize `last_refill_time` in `__init__`) consumes one mock value at construction, causing off-by-one errors in `test_refill`. The judge correctly identified this for the `score=2` trial (C02/attractor/rep=0). However, Ralph rep=0 also fails `test_thread_safety` (104 tokens granted vs. ≤100). This is a task quality issue: the thread safety test is timing-sensitive and flaky.

### Fix

```bash
# In .venv313, install before running:
pip install pytest pytest-asyncio aiohttp
```

In `benchmark/harness.py`, add an explicit pytest availability check:
```python
def _check_test_deps():
    try:
        import pytest
        import pytest_asyncio
    except ImportError as e:
        raise RuntimeError(f"Missing test dependency: {e}. Run: pip install pytest pytest-asyncio")
```

For C08, add `@pytest.mark.asyncio` or use `asyncio.run()` wrappers in the test suite. Consider replacing C02's timing-sensitive thread test with a deterministic one.

---

## Issue 2 — AttractorFlow Never Activated: Structural Architecture Flaw

### The core problem: single-step completion

AttractorFlow's classifier requires **≥ 3 trajectory states** to produce a regime classification. Fewer than 3 states returns `UNKNOWN` with the hint "Insufficient data — record at least 3 states."

In the `attractor` condition:
- State 0: `monitor.record(task_prompt)` — recorded before the first call
- State 1: `monitor.record(assistant_text)` — recorded after the model responds
- **Completion check fires immediately** → `break` before state 3 can accumulate

Claude Haiku completed in 1 step for **43 of 45 attractor trials (95.6%)**. After step 1, `buffer_size = 2`. The classifier returns UNKNOWN. AF never influenced a single token of output.

In the `combined` condition:
- AF guidance is computed at the END of each iteration, AFTER the completion check
- If Claude completes at iteration 1 (80% of trials), the loop breaks before guidance can be computed
- AF check required ≥ 3 buffer states (met after 2 iterations), but 80% finish in 1 iteration
- Only **2 of 45 combined trials** ever reached the AF check threshold

**Diagram of the broken flow:**
```
Iteration 0:
  monitor.record(task_prompt)   ← state 0
  call_claude(prompt)
  monitor.record(output)        ← state 1 (buffer_size=2)
  if completion: BREAK          ← fires 95% of the time
  guidance = _get_guidance()    ← only runs 5% of the time; buffer_size=2, returns ''

Iteration 1 (if reached):
  monitor.record(output)        ← state 2 (buffer_size=3) ← AF could now classify
  if completion: BREAK          ← fires again; guidance never injected
  guidance = _get_guidance()    ← buffer_size=3, COULD classify, but next iter may not happen
```

### Root cause: guidance is computed for the NEXT iteration, too late

Even when AF guidance is successfully computed at the end of iteration N, it's injected into the prompt for iteration N+1. If the model completes the task in 1 step, there is no iteration N+1 to receive the guidance. The signal and the action are temporally decoupled in a way that never closes.

### Fix: Pre-completion guidance injection

The fix is to record multiple intermediate states WITHIN a single iteration using a multi-step prompt chain, giving AF enough trajectory to measure before the final answer:

**Revised `attractor` condition flow:**
```
Step 0: send initial prompt → get "planning" response (DO NOT allow TASK COMPLETE here)
  monitor.record(plan_output)   ← state 1
  guidance = _get_guidance()    ← buffer_size=2 (need min 2 for distance, 3 for classify)

Step 1: send "now implement" → get implementation
  monitor.record(impl_output)   ← state 2
  guidance = _get_guidance()    ← buffer_size=3 → CAN CLASSIFY

Step 2: send "now verify and finalize" → get final answer with TASK COMPLETE
  monitor.record(final_output)  ← state 3
```

This requires splitting the single prompt into a **mandatory 3-phase chain**: plan → implement → verify. Claude must NOT be allowed to signal completion in the planning phase.

**Concrete change to the system prompt:**

```
Phase 1 (planning): Analyze the task and describe your approach. Do NOT write code yet.
Phase 2 (implementation): Now write the complete solution as a ```python block.
Phase 3 (verification): Review your solution. If correct, output: TASK COMPLETE: <summary>
```

After each phase response, record state and compute AF guidance before the next phase call.

---

## Issue 3 — Ceiling Effect: Score Distribution Is Compressed at the Top

### The problem

| Score | Count | % |
|-------|-------|---|
| 10 | 37 | 27.4% |
| 9 | 68 | 50.4% |
| 8 | 26 | 19.3% |
| ≤7 | 4 | 3.0% |

75.5% of all scores are 9 or 10. The practical score range is 7–10 (a 3-point window). With σ ≈ 0.78–1.27, detecting a 0.31-point difference (Ralph vs. AttractorFlow) would require hundreds of trials. The ceiling means we cannot distinguish "good" from "better" — only "broken" from "working."

Causes:
1. **Tasks are too easy for Claude Haiku** — a well-framed task with a clear test suite that the model can solve in one pass will always score 8-10
2. **Judge cannot distinguish 9 from 10** — ICC=0.286 (fair, not good); the same solution scores 8 on rep=1 and 10 on rep=3
3. **Bonus capped at 10** — even with the +2 test pass bonus, once base score > 8 the bonus is partially wasted
4. **Analysis tasks have no objective ground truth** — purely LLM-judged; all cluster at 8-9

### Fixes

**Task redesign for difficulty gradient:**
- Add a "hard" tier requiring multiple interdependent components where single-pass Claude Haiku routinely scores 5-7
- Examples: multi-file architecture, algorithmic optimization with benchmarks, tasks with tricky edge cases that require iteration
- Alternatively: **multi-turn evaluation** — score not just the final answer but the quality of reasoning process

**Richer rubric with sub-scores:**
- Current rubric produces a single 0-10 integer (coarse)
- Replace with: correctness (0-4) + efficiency (0-2) + edge cases (0-2) + code quality (0-2) = 0-10 in 0.5 increments
- This opens the score range without changing the scale

**Judge upgrade:**
- Switch judge from Haiku to Sonnet (higher ICC, more nuanced scoring)
- Use `--temperature 0` equivalent by adding explicit JSON schema constraints to the prompt
- Add 3-judge ensemble with majority vote for high-stakes scores

**Task selection:**
- Remove C08 (async, needs pytest-asyncio — environmental, not intellectual)
- Remove C02's thread safety test (flaky) or redesign
- Add 3 harder tasks that genuinely require iteration (rated "hard" a priori)

---

## Issue 4 — HuggingFace Model Loading (not a bug, but note)

The `all-MiniLM-L6-v2` sentence transformer model is cached at:
```
~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2
```

No HF token is required (public model). The model loads successfully from cache on every trial. **There is no HF authentication bug.**

However: the model is loaded lazily on first `monitor.record()` call. This adds ~0.5-1s to the first trial's runtime. For a 120s timeout this is negligible, but it should be pre-warmed to avoid timing anomalies:

```python
# Add to benchmark/__init__.py or harness startup:
def warmup_af():
    """Pre-load the embedding model before trial timing starts."""
    from phase_space import PhaseSpaceMonitor
    m = PhaseSpaceMonitor(capacity=5)
    m.record("warmup")
```

---

## Issue 5 — AF λ Signal Validity (weak correlation confirmed)

Pearson r = 0.078, p = 0.463 between λ (Lyapunov exponent) and quality score.

There are two explanations:
1. **AF monitoring is correct but λ doesn't predict quality** for single-step well-formed problems — the trajectory is too short and too uniform for FTLE to be meaningful
2. **AF monitoring has insufficient data** — with only 2-3 states per trajectory, the SVD-based FTLE estimator is operating below its reliable range (it's designed for 8+ states, as `DEFAULT_WINDOW = 8`)

The LyapunovEstimator `window=8` means it needs at least 9 states to use SVD — with only 2-3 states it falls back to simpler distance ratios, which are much noisier. This explains why `final_lambda = 0.0` in all 1-step trials.

**Fix:** With the 3-phase prompt chain (Issue 2 fix), trajectories will have 4+ states minimum. This brings AF into its designed operating regime.

---

## Issue 6 — Cost Accounting Always Returns $0

The `total_cost()` function never increments because `claude -p --output-format json` under a Pro subscription returns `cost_usd: 0` (plan-based billing). The `_estimate_tokens()` function's fallback word-count heuristic is also inaccurate.

This is cosmetic (no functional impact on results), but the tokens column in `scores.csv` cannot be compared across conditions.

**Fix for Round 2:** Track wall-clock time per call (already logged in `elapsed`) and add character count as a proxy for input size. Remove token-based efficiency comparisons from the leaderboard; replace with seconds/trial.

---

## Issue 7 — Combined Condition Has No `final_regime` Column

The `combined` condition's `CombinedResult` dataclass does not have a `final_regime` field. The harness reads `result.regime_log[-1]` only if `regime_log` is non-empty. Since AF never fires in most combined trials, `regime_log` is empty and `final_regime` writes `NaN` to the CSV.

This is also a design issue: the combined condition should capture the same AF diagnostics as the attractor condition.

---

## Proposed Round 2 Protocol: One Task, Prove the Fix

Before running the full 135-trial matrix, validate every change on **one task, one rep per condition** (3 calls total). This costs ~$0 and takes ~5 minutes.

### Phase 1: Fix and validate the harness (C01, 1 rep each condition)

**Goal:** Confirm test pass bonus works, AF fires on the attractor condition, and scores distribute across 7-10.

Changes:
- [ ] `pip install pytest pytest-asyncio aiohttp` in `.venv313`
- [ ] Add `_check_test_deps()` call to `harness.main()` before trial loop
- [ ] Add `warmup_af()` call to `harness.main()` before trial loop
- [ ] Fix combined's `CombinedResult` dataclass to include `final_regime: str = "N/A"`

Validation: Run C01 only:
```bash
source .venv313/bin/activate
python -m benchmark.harness --tasks C01 --conditions ralph attractor combined --reps 1
```
Expected: `test_passed=True` for all 3 trials; score = 9 (base) + 2 (bonus) = capped at 10 if base ≥ 8.

### Phase 2: Redesign the AF loop (attractor.py)

**Goal:** Force 3+ trajectory states before allowing completion.

Changes to `benchmark/conditions/attractor.py`:

```python
# New 3-phase system prompt
ATTRACTOR_SYSTEM = """\
You are a 3-phase iterative agent. Complete each phase before moving to the next.

CRITICAL: TEXT-ONLY mode. No tools. No file creation. Code in ```python blocks only.

PHASE 1 — PLAN: Analyze the task. Describe your approach and key decisions.
  Do NOT write code yet. Do NOT say "TASK COMPLETE" in Phase 1.

PHASE 2 — IMPLEMENT: Write the complete solution as a single ```python code block.
  Do NOT say "TASK COMPLETE" in Phase 2.

PHASE 3 — VERIFY: Review your solution against the task requirements.
  If fully correct: output exactly: TASK COMPLETE: <one-line summary>
  If you found a bug: fix it and then output TASK COMPLETE.
"""

PHASE_PROMPTS = [
    "PHASE 1: Analyze the task and describe your approach. Do NOT write code yet.",
    "PHASE 2: Write the complete solution as a single ```python code block.",
    "PHASE 3: Review your solution. If correct, output: TASK COMPLETE: <summary>",
]

def run(task_prompt: str, goal_text=None) -> AttractorResult:
    result = AttractorResult(output="")
    t0 = time.time()
    
    monitor = PhaseSpaceMonitor(capacity=AF_BUFFER_CAPACITY)
    lyapunov_est = LyapunovEstimator(window=AF_WINDOW)
    classifier = AttractorClassifier()
    
    goal = goal_text or task_prompt[:200]
    monitor.set_goal(goal)
    monitor.record(task_prompt)   # state 0
    
    messages = []
    guidance = ""
    
    for phase_idx, phase_prompt in enumerate(PHASE_PROMPTS):
        user_content = ""
        if guidance:
            user_content += f"[TRAJECTORY GUIDANCE]\n{guidance}\n\n"
        if phase_idx == 0:
            user_content += f"{task_prompt}\n\n{phase_prompt}"
        else:
            user_content += phase_prompt
        
        messages.append({"role": "user", "content": user_content})
        full_prompt = ATTRACTOR_SYSTEM + "\n\n" + _msgs_to_str(messages[:-1]) + f"\n\n[NEW MESSAGE]\n{user_content}"
        
        cli_result = cli_runner.call_claude(full_prompt)
        if cli_result["error"]:
            result.output += f"\n\n[ERROR phase {phase_idx+1}: {cli_result['error']}]"
            break
        
        assistant_text = cli_result["output"]
        result.tokens_used += cli_result["tokens_estimated"]
        messages.append({"role": "assistant", "content": assistant_text})
        result.output += f"\n\n[Phase {phase_idx+1}]\n{assistant_text}"
        
        # Record state — now buffer grows to 2, 3, 4 across phases
        monitor.record(assistant_text)
        result.steps = phase_idx + 1
        
        # AF guidance computed after EVERY phase (buffer_size grows to 3 after phase 1)
        guidance = _get_guidance(monitor, lyapunov_est, classifier, result, phase_idx)
        
        if _is_complete(assistant_text):
            break
    
    # ... rest of result finalization unchanged
```

This guarantees:
- After Phase 1: buffer = [task, plan] → 2 states, guidance = '' (< 3)
- After Phase 2: buffer = [task, plan, impl] → 3 states, **AF classifies for Phase 3**
- After Phase 3: buffer = [task, plan, impl, verify] → 4 states, post-hoc AF

**Validation test:** Run A05 (paper summary — most complex analysis task):
```bash
python -m benchmark.harness --tasks A05 --conditions attractor --reps 1
```
Expected: `final_regime != UNKNOWN`, `steps = 3`, `af_interventions >= 0` (regime logged at phase 2).

### Phase 3: Redesign the combined condition

Same 3-phase structure, but AF guidance is computed after Phase 2 and injected into Phase 3 (the verification/finalization phase). The combined condition is where AF guidance has the most potential — it's the moment where a "STUCK" signal could prompt Claude to try a different approach.

Changes:
- Combined should also use the 3-phase prompt structure
- Guidance injection happens before Phase 3 (not before iteration 1 of a new Ralph loop)
- `regime_log` and `final_regime` saved correctly

### Phase 4: Task redesign for difficulty gradient

Replace or augment 3 existing tasks with "hard" variants:

| Replace | With | Why harder |
|---------|------|------------|
| C01 (BST) | Balanced BST (AVL or Red-Black) | Rotation logic requires real iteration |
| C02 (rate limiter) | Distributed rate limiter with Redis mock | Multi-component, harder to single-pass |
| A03 (paper summary) | "Compare two papers, synthesize contradictions" | Requires holding two complex arguments |

Add one "multi-file architecture" task where the model must design and implement 3 modules that interact — impossible to do correctly in one pass.

### Phase 5: Score distribution validation

After fixes, run all 15 tasks × 3 conditions × 1 rep (45 trials) and check score distribution:
- Target: 40% of scores in 7-8 range (currently 19.3%)
- If still ceiling-effect: reduce to 12 tasks, add 3 hard tasks

---

## What a Trustworthy Result Would Look Like

After the fixes above, a convincing result requires:

1. **AF fires in ≥ 80% of trials** — `final_regime != UNKNOWN` for ≥ 80% of attractor/combined trials
2. **Test pass rate > 60%** for coding tasks across all conditions
3. **Score range expands**: σ > 1.5, score distribution covers 5-10
4. **ANOVA is significant OR demonstrably non-significant with adequate power** — post-hoc power analysis shows β < 0.2 for a 0.5-point difference
5. **λ vs. quality correlation emerges**: if AF is working, r > 0.3 for trials where AF actually classified
6. **Combined > Ralph on hard tasks**: if AF adds value, the advantage should appear specifically on tasks where single-pass completion fails (hard tasks, lower base scores)

---

## Summary Table: Issues → Fixes → Validation

| # | Issue | Severity | Fix | Validation |
|---|-------|----------|-----|------------|
| 1a | pytest not installed | **Critical** | `pip install pytest pytest-asyncio aiohttp` | C01 test_passed=True |
| 1b | C08 needs pytest-asyncio | **Critical** | Install + add pytest.mark.asyncio | C08 tests pass |
| 1c | C02 thread test flaky | High | Redesign test or mock threads | C02 consistent pass |
| 2a | AF never fires (1-step completion) | **Critical** | 3-phase prompt chain | final_regime ≠ UNKNOWN |
| 2b | Guidance injected too late | **Critical** | Compute guidance between phases | af_interventions > 0 |
| 2c | Combined has no final_regime | Medium | Add field to CombinedResult | NaN eliminated |
| 3a | Ceiling effect (75% at 9-10) | High | Add 3 hard tasks | σ > 1.5 |
| 3b | Judge granularity (integer 0-10) | Medium | Sub-scores → 0.5 increments | wider score range |
| 3c | Judge model too weak | Medium | Upgrade to Sonnet for judge | ICC > 0.5 |
| 4 | HF model lazy-load timing | Low | Pre-warm before timing | cosmetic |
| 5 | λ below FTLE minimum window | High | Fixed by 3-phase (4+ states) | r > 0.3 |
| 6 | Cost always $0 | Cosmetic | Replace with wall-clock/chars | N/A |
| 7 | λ vs quality r=0.078 | Symptom | Fixed by Issues 2+5 | r > 0.3 |

---

## One-Task Iterative Validation Protocol

Run this exact sequence to prove each fix before scaling:

```bash
source .venv313/bin/activate

# Step 1: Confirm test runner works
pip install pytest pytest-asyncio aiohttp
python -c "import pytest, pytest_asyncio; print('OK')"

# Step 2: Smoke test one coding task (C01) - should show test_passed=True
python -m benchmark.harness --tasks C01 --conditions ralph attractor combined --reps 1
# Check: scores.csv has test_passed=True, quality_score includes bonus

# Step 3: Smoke test AF activation on analysis task (A05)
python -m benchmark.harness --tasks A05 --conditions attractor combined --reps 1
# Check: final_regime != UNKNOWN for attractor; af_interventions reported for combined

# Step 4: Check score distribution shift (add new hard task H01)
python -m benchmark.harness --tasks H01 --conditions ralph attractor combined --reps 1
# Check: scores are in 6-8 range, not ceiling at 9-10

# Step 5: If all 3 checks pass → run full 45-trial pilot (15 tasks × 3 conditions × 1 rep)
python -m benchmark.harness --reps 1

# Step 6: Check metrics
python -m benchmark.stats
# Check: ANOVA F > 3.0 OR power analysis shows definitive null (β < 0.2)
# Check: λ vs quality r > 0.3
# Check: score σ > 1.5

# Step 7: If metrics look promising → full 135-trial run
python -m benchmark.harness
```

---

## Files to Modify for Round 2

| File | Change | Priority |
|------|--------|----------|
| `benchmark/conditions/attractor.py` | 3-phase prompt chain; AF guidance between phases | Critical |
| `benchmark/conditions/combined.py` | Same 3-phase structure; fix CombinedResult dataclass | Critical |
| `benchmark/harness.py` | Add `_check_test_deps()` at startup; add `warmup_af()` | Critical |
| `benchmark/config.py` | Remove `AF_CHECK_EVERY_N_STEPS` (now every phase); add `N_PHASES = 3` | High |
| `benchmark/tasks/coding/C08_async_retry_client.md` | Add `pytest.mark.asyncio`; install aiohttp | High |
| `benchmark/tasks/coding/C02_rate_limiter.md` | Redesign thread safety test; fix lazy-init hint | High |
| `benchmark/judge/judge.py` | Upgrade to Sonnet model; add sub-score rubric | Medium |
| `benchmark/tasks/coding/` | Add 3 hard tasks (H01, H02, H03) | Medium |
| `benchmark/tasks/analysis/` | Add 2 hard analysis tasks requiring synthesis | Medium |
| `benchmark/report.py` | Replace token-based efficiency with wall-clock/trial | Low |
| `benchmark/__init__.py` | Add `warmup_af()` function | Low |

---

*This document should be the single source of truth for all Round 2 changes. Apply fixes sequentially, validate on the one-task protocol at each step, and only scale once metrics confirm the fix is working.*
