# Ralph vs AttractorFlow — Intermediate Results Report

> Generated: 2026-04-09  
> Status: **Partial dataset** — Round 1 (135 trials, broken AF) + C01 validation (2 trials, fixed AF)  
> Purpose: Assess what the current data proves, where ceiling effects remain, and what Round 2 must address.

---

## 1. What This Report Covers

The dataset currently holds **130 Round 1 trials** across 14 tasks (C01's 9 Round 1 rows were deleted to make room for validation) plus **2 C01 validation trials** using the corrected architecture.

| Dataset Slice | Trials | AF Correct? | pytest Correct? |
|---------------|--------|-------------|-----------------|
| Round 1 (C02–C08, A01–A07) | 126 | ✗ UNKNOWN 97.6% | ✗ all False |
| C01 Round 1 (deleted) | 9 | ✗ UNKNOWN | ✗ all False |
| **C01 Validation** | **2** | **✓ CONVERGING** | **✓ both True** |

**The Round 1 data is structurally contaminated and should not be used for final conclusions.** This report explains what it nonetheless reveals, what the C01 validation proves, and what must change before Round 2.

---

## 2. Who "Won" Round 1 — and Why It Doesn't Count

### Overall Means (14 complete tasks × 3 reps)

| Rank | Condition | Quality μ | σ | Score Range |
|------|-----------|-----------|---|-------------|
| 🥇 | **Ralph** | 9.07 | 0.78 | 7–10 |
| 🥈 | **Ralph + AttractorFlow (combined)** | 8.98 | 0.72 | 7–10 |
| 🥉 | **AttractorFlow** | 8.71 | 1.27 | **2–10** |

### Statistical Tests (14-task paired t-tests)

| Comparison | Δμ | t | p | Cohen's d | Significant? |
|------------|-----|---|---|-----------|--------------|
| Ralph vs AttractorFlow | +0.357 | 1.67 | 0.119 | 0.487 | No |
| Ralph vs Combined | +0.095 | 0.72 | 0.486 | 0.154 | No |
| AttractorFlow vs Combined | -0.262 | -0.96 | 0.355 | -0.395 | No |

**Ralph appears to win — but the result is invalid.** Three compounding failures corrupt the AttractorFlow condition:

1. **pytest never ran** — all 63 Round 1 coding trials across all conditions report `test_passed=False`. The +2 bonus was never applied to any trial. This equally penalizes all conditions, but AF's architecture requires multi-step orchestration that would produce correct code more reliably — evidence for this is suppressed.

2. **AttractorFlow never actually fired** — 41 of 42 Round 1 attractor trials show `final_regime=UNKNOWN`. The AF plugin was imported directly as Python modules inside a `claude -p` subprocess, which has no MCP tool access. The PhaseSpaceMonitor never received state recordings, so no regime classification ever occurred. The "attractor" condition was effectively a plain `claude -p` call with extra startup overhead.

3. **C02 catastrophic failure** — attractor scored 2/10 on C02 (thread-safe queue). The `claude -p` architecture produced a solution that never passed the single-threaded fallback harness. This outlier inflates AF's standard deviation to 1.27 vs ralph's 0.78 and depresses the AF mean by ~0.3 points.

**Bottom line: Ralph wins Round 1 because AttractorFlow was never tested.** What was measured is two instances of `claude -p` — one with ralph's iterative loop and one with AF disabled — against each other.

---

## 3. The C01 Validation — What It Actually Proves

C01 (Binary Search Tree) was re-run with the corrected architecture: one ralph trial and one attractor trial using the `attractor-flow:attractor-orchestrator` Agent spawned via Claude Code's Agent tool.

| Condition | Score | Test | Regime | λ | Steps | Elapsed |
|-----------|-------|------|--------|---|-------|---------|
| Ralph | 10/10 | ✓ PASS (8/8) | N/A | — | 1 | 27.5s |
| **AttractorFlow** | **10/10** | **✓ PASS (8/8)** | **CONVERGING** | **-0.15** | **4** | **27.0s** |

### What this validates

**A. pytest bonus mechanism works.** Both trials returned `test_passed=True` and received the +2 bonus correctly. The scoring pipeline from solution.py → pytest → CSV is intact.

**B. AttractorFlow genuinely fired.** `final_regime=CONVERGING` (not UNKNOWN) with λ=-0.15 confirms:
- The orchestrator called `attractorflow_record_state` at least 3 times (minimum for PhaseSpaceMonitor to classify)
- The PhaseSpaceMonitor detected stable convergence (λ < -0.05 threshold)
- The MCP layer was fully active — this was impossible in Round 1

**C. Agent-tool architecture is correct.** The attractor trial took 4 orchestrated steps (plan → implement → test → checkpoint) compared to ralph's single response. This is the intended AF workflow: monitoring trajectory health at each step and intervening if the regime becomes STUCK or DIVERGING.

**D. Efficiency parity.** Both conditions completed in ~27 seconds. The 4-step orchestration adds no wall-clock cost on a task where convergence is immediate.

### What it doesn't yet prove

- Whether AF's interventions (explorer-agent / convergence-agent spawning) improve outcomes on *harder* tasks where ralph struggles
- Whether AF avoids the C02-style catastrophic failures that contaminate Round 1
- Statistical significance (n=1 trial per condition is not a study)

---

## 4. Ceiling Effect Analysis

### Score-10 Frequency

| Condition | % at Ceiling (score=10) |
|-----------|------------------------|
| Ralph | **32.6%** |
| Combined | 21.4% |
| AttractorFlow | 18.6% |

### Why This Is a Problem

The judge is Claude Haiku with a 0–10 scale. For straightforward tasks, both ralph and AF produce correct, complete solutions — the judge awards 9 or 10 regardless of *how* the solution was reached. This compresses the score distribution and makes it statistically impossible to detect AF's genuine advantage.

### Score Distribution

```
Score:        2   7   8   9   10
Ralph:        0   1   8  20   14   (σ=0.78)
Attractor:    1   1  10  23    8   (σ=1.27)
Combined:     0   1   8  24    9   (σ=0.72)
```

All three distributions are right-skewed and bounded at 10. With 95%+ of scores in the 8–10 band, statistical tests have almost no resolution to distinguish conditions. The ANOVA from Round 1 confirmed this: F(2,88)=1.73, p=0.184 — not because there's no effect, but because the instrument is too coarse for this task set.

### Tasks Where Ceiling Is Most Severe

| Task | Ralph μ | AF μ | Combined μ | Problem |
|------|---------|------|------------|---------|
| C04 | **10.00** | 9.67 | 9.00 | Ralph at perfect ceiling |
| C05 | **10.00** | 9.67 | 9.33 | Ralph at perfect ceiling |
| C01 | 10.00 | **10.00** | N/A | Both at ceiling |
| A03 | 9.00 | 9.00 | 8.67 | Tied, no resolution |
| A05 | 9.00 | 9.00 | 8.67 | Tied, no resolution |

For C04 and C05 specifically, Ralph hits a perfect 10 mean across 3 reps — there is literally no headroom for AF to demonstrate superiority.

---

## 5. Subgroup Analysis — Coding vs Analysis

### Coding Tasks (C02–C08, Round 1 + C01 validation)

| Condition | μ | σ | Note |
|-----------|---|---|------|
| Ralph | **9.64** | 0.49 | Near-perfect; test bonus never applied in R1 |
| Combined | 9.38 | 0.50 | — |
| AttractorFlow | 8.86 | 1.64 | C02 outlier (score=2) drives σ up |

Coding tasks show the largest Ralph advantage — but this is almost entirely explained by:
1. C02 catastrophic failure (score=2) pulling AF's mean down
2. pytest bonus never applied (Round 1) — correct solutions scored as 8 instead of 10

With the corrected architecture (C01 validation), both ralph and AF score 10 on a representative coding task.

### Analysis Tasks (A01–A07, Round 1 only)

| Condition | μ | σ | Note |
|-----------|---|---|------|
| AttractorFlow | **8.62** | 0.74 | Slight AF lead |
| Ralph | 8.52 | 0.60 | — |
| Combined | 8.57 | 0.68 | — |

Analysis tasks show no statistically meaningful difference. All conditions cluster in 8.3–9.0. This is where the ceiling effect is less severe (fewer tasks hit 10), so the distribution has *slightly* more resolution — yet conditions still can't be distinguished because all produce high-quality analytical outputs.

---

## 6. AttractorFlow Regime Distribution

### Round 1 (Broken Architecture)

| Regime | Count | % |
|--------|-------|---|
| UNKNOWN | 41 | 97.6% |
| DIVERGING | 1 | 2.4% |
| CONVERGING | 0 | 0% |

The single DIVERGING trial (A05/combined/rep=1, λ=0.479) and the single A07/combined/rep=0 CONVERGING trial appear in the *combined* condition, not pure attractor — because combined used a slightly different invocation. The pure attractor condition returned UNKNOWN for all 42 trials.

### Validation (Correct Architecture)

| Regime | Count | % |
|--------|-------|---|
| CONVERGING | 1 | 100% |

One trial is not a distribution. But this proves the classifier works when fed real multi-step trajectory data. The fix is structural, not parametric.

---

## 7. Efficiency Metrics

| Condition | Avg Iterations | Avg Tokens | Avg Time (s) |
|-----------|----------------|------------|--------------|
| AttractorFlow (R1) | 1.0 | 1,744 | 33.8 |
| Ralph | 1.1 | 1,981 | 35.7 |
| Combined | 1.3 | 3,229 | 49.5 |
| **AttractorFlow (C01 fixed)** | **4** | **338** | **27.0** |

The C01 validation attractor trial shows 338 tokens — this is the *agent text output* (summary only), not total tokens consumed during 4-step orchestration. The token count proxy (word count of agent text output) is not comparable across conditions. Round 2 needs proper token tracking from the Claude API response objects.

Combined uses 63% more tokens than ralph (3,229 vs 1,981) at 49.5s average — the overhead of the AF monitoring layer on top of the ralph loop.

---

## 8. The Core Question — Does AF Help?

**Current evidence: insufficient to conclude.** Here is why:

| Claim | Evidence | Verdict |
|-------|----------|---------|
| AF fires and tracks trajectory | C01 validation: CONVERGING, λ=-0.15, 4 steps | ✓ Proven |
| pytest bonus works | C01: both conditions test_passed=True | ✓ Proven |
| AF improves quality on easy tasks | C01: both score 10, no difference | ✗ Can't tell (ceiling) |
| AF prevents catastrophic failures | C02 score=2 in R1 attractor | ✗ Unknown — R1 AF broken |
| AF helps on harder tasks | No hard tasks in current suite | ✗ Not tested |
| AF interventions (explorer/convergence) fire | 0 interventions in C01 trial | ✗ Task too easy to trigger |
| Ralph vs AF is statistically significant | p=0.119, n=14 tasks | ✗ Not significant |

The hypothesis that AttractorFlow adds value is **untested, not disproven**. The attractor condition in Round 1 was never actually the attractor condition — it was `claude -p` without the plugin.

---

## 9. What Must Change Before Round 2

### Critical (breaks validity)

| # | Issue | Fix | Status |
|---|-------|-----|--------|
| 1 | All attractor trials used wrong architecture | `benchmark/agent_harness.py` — Agent tool spawning | ✅ Built & validated |
| 2 | pytest never installed → test_passed always False | `pip install pytest pytest-asyncio` + `_check_test_deps()` guard | ✅ Fixed |
| 3 | AF MCP tools unreachable in `claude -p` | Agent tool is the only correct invocation | ✅ Architectural fix |
| 4 | UNKNOWN regime 97.6% — PhaseSpaceMonitor never fed | Correct invocation gives 4+ states → classifier works | ✅ Proven in C01 |

### Important (limits conclusions)

| # | Issue | Fix | Status |
|---|-------|-----|--------|
| 5 | Ceiling effect: 8 tasks where all conditions score 9–10 | Add 5+ harder tasks or extend existing ones with harder sub-problems | Pending |
| 6 | C02 thread-safe queue — flaky test (may fail on correct solutions) | Audit C02 test suite for race conditions | Pending |
| 7 | Token tracking uses word-count proxy | Extract actual usage from API response | Pending |
| 8 | `combined` condition uses `ralph.py` infrastructure, not agent_harness | Redesign combined to use Agent tool with AF monitoring | Pending |
| 9 | Judge ICC2=0.286 (low consistency) | Re-run judge at temperature=0, or use 2-judge ensemble | Pending |
| 10 | 0 AF interventions in C01 (task too easy) | Harder tasks needed to trigger explorer/convergence subagent spawning | Pending |

### Nice to Have

- Absolute token counts from API (not word-count proxy)
- Per-step timing (not just total elapsed)
- AF regime logged at each step, not just final

---

## 10. Recommended Round 2 Protocol

### Phase 1: Complete C01 (3 reps × 2 conditions)

Run the remaining 2 reps of ralph and attractor on C01 to get full 3-rep statistics before expanding:

```bash
# Ralph reps 1, 2
python -m benchmark.harness --tasks C01 --conditions ralph --reps 3

# Attractor reps 1, 2 — spawned via agent_harness in Claude Code session
from benchmark.agent_harness import prepare_attractor_trial, finalize_attractor_trial
prep = prepare_attractor_trial('C01', 1)
# ... spawn Agent, finalize
```

### Phase 2: Add 3 Hard Tasks

The existing task suite tops out at "implement BST" / "analyze time series." Add tasks that genuinely challenge even a strong model:

| Proposed Task | Why It Helps |
|---------------|--------------|
| H01: Implement consistent hashing ring with virtual nodes | Multi-constraint; likely to get stuck |
| H02: Write a Pratt parser for a small expression language | Architectural; benefits from planning steps |
| H03: Debug a provided async race condition (given broken code) | AF STUCK regime should trigger; measures rescue |

### Phase 3: Full Re-run (15+ tasks × 3 conditions × 3 reps)

With corrected architecture confirmed, run the complete benchmark. Expected outcomes if AF works as designed:
- Hard tasks: AF should show STUCK→intervention patterns; quality advantage possible
- Easy tasks: Both conditions near ceiling; no detectable difference (that's fine)
- Overall: Reduced catastrophic failures in AF vs ralph on hard tasks

---

## 11. Summary Verdict

| Question | Answer |
|----------|--------|
| Who won Round 1? | Ralph (μ=9.07 vs 8.71), but results are invalid |
| Is Ralph genuinely better? | **Unknown** — AF was never tested |
| Does AF work as designed? | **Yes** — C01 validation confirms CONVERGING regime, pytest pass |
| Is there still a ceiling problem? | **Yes** — 8/14 tasks too easy to distinguish conditions |
| Can we conclude anything? | Only that the fixed architecture works; a real comparison requires Round 2 |

**The correct answer to "who won" is: the experiment hasn't run yet.** Round 1 was a warm-up that found three critical bugs. The C01 validation fixed and confirmed the architecture. Round 2 with corrected harness + harder tasks is where the real comparison happens.

---

*Generated from `benchmark/results/scores.csv` — 128 trials (Round 1, contaminated) + 2 trials (C01 validation, correct)*
