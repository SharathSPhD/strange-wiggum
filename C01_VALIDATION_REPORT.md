# C01 Validation Run — Architecture Fix & Results

> Date: 2026-04-09  
> Task: C01 — Binary Search Tree (8 pytest cases)  
> Conditions: ralph (1 rep) + attractor (1 rep)  
> Purpose: Prove the corrected harness and AF integration actually work

---

## 1. What Was Wrong (Why This Run Was Needed)

Round 1 had two architectural bugs that made the attractor condition meaningless:

**Bug 1 — AttractorFlow never used MCP tools.**  
The attractor condition was calling `claude -p` as a subprocess and importing AF Python modules directly. `claude -p` has no access to Claude Code's Agent tool or MCP servers. The PhaseSpaceMonitor received zero state recordings, so the regime classifier always returned `UNKNOWN`. The "attractor condition" was silently just another stateless subprocess call.

**Bug 2 — pytest was never installed.**  
All 72 Round 1 coding trials returned `test_passed=False` regardless of correctness. The +2 bonus for passing tests was never applied to any trial. A correct BST scored 8 instead of 10.

---

## 2. What Was Changed

### New file: `benchmark/agent_harness.py`

A two-phase helper that wraps attractor trials around Claude Code's Agent tool — the only way AF MCP tools can fire.

**Phase 1 — `prepare_attractor_trial(task_id, rep)`**
- Loads the task spec and extracts the pytest suite from the markdown
- Creates a persistent temp directory (e.g. `/tmp/attractor_C01_abc123_xyz/`)
- Writes `test_solution.py` to the temp dir so the agent can run tests via Bash
- Saves `_trial_meta.json` with task spec for later scoring
- Returns `{trial_uuid, temp_dir, agent_prompt}` — everything needed to spawn the Agent

**Phase 2 — `finalize_attractor_trial(...)`**
- Reads `solution.py` from the temp dir (written by the agent using the Write tool)
- Runs `pytest test_solution.py` against that file
- Appends `solution_code` to the judge submission if the agent didn't include a code block in its text (so the judge always sees the actual implementation)
- Writes the scored row to `scores.csv`, updates the blind manifest, cleans up temp dir

**The agent prompt instructs the orchestrator to:**
1. Call `attractorflow_record_state` after each meaningful step
2. Check `attractorflow_get_regime` every 2–3 steps
3. Spawn explorer-agent if STUCK, convergence-agent if CONVERGING and near done
4. Write the final solution to `temp_dir/solution.py` using the Write tool
5. Run tests via Bash: `cd temp_dir && python -m pytest test_solution.py -v`
6. Output a code block + AF summary in the final text response

### Modified: `benchmark/harness.py`

Two guards added to `main()` (only run when `--dry-run` is not set):

- `_check_test_deps()` — validates `import pytest, pytest_asyncio` or exits with install instructions. Prevents silent test failures.
- `_warmup_af()` — pre-loads the MiniLM sentence-transformer before trial timing starts. Prevents the first trial from absorbing model download latency.

---

## 3. The Run

### Ralph — C01, rep 0

Invoked via the existing harness:
```
python -m benchmark.harness --tasks C01 --conditions ralph --reps 1
```

Ralph's `claude -p` loop ran one iteration. The model produced a complete BST implementation with a `Node` inner class. The harness extracted the `python` code block, wrote it to a temp dir alongside the pre-extracted test suite, and ran pytest.

**pytest result: 8/8 PASS**

The judge received the full agent output including solution code. Base score: 8. +2 bonus applied (test_passed=True). Final: **10/10**.

### Attractor — C01, rep 0

Prepared via `prepare_attractor_trial('C01', 0)`, then the `attractor-flow:attractor-orchestrator` Agent was spawned in this Claude Code session with the generated prompt.

**Orchestrator execution — 4 steps:**

| Step | Action | AF Tool Called |
|------|--------|----------------|
| 1 | Analyzed task, planned BST structure | `attractorflow_record_state("Analyzed requirements...")` |
| 2 | Implemented full BST with all methods | `attractorflow_record_state("Implementation complete...")` |
| 3 | Ran pytest (8/8 pass), verified | `attractorflow_record_state("Tests passing...")`  |
| 4 | Checkpoint — stable solution confirmed | `attractorflow_checkpoint()` |

After 3 state recordings, PhaseSpaceMonitor had enough data to classify the trajectory.  
**Regime: CONVERGING (λ = -0.15)**

The agent wrote `solution.py` to the temp dir using the Write tool. `finalize_attractor_trial()` read it (3,837 chars), ran pytest independently, confirmed 8/8 pass, scored via judge.

**pytest result: 8/8 PASS**  
Base score: 10. +2 bonus applied. Final capped at **10/10**.

---

## 4. Results

| Condition | Score | Test | Regime | λ | Steps | Time |
|-----------|-------|------|--------|---|-------|------|
| Ralph | **10/10** | ✓ 8/8 PASS | N/A | — | 1 | 27.5s |
| AttractorFlow | **10/10** | ✓ 8/8 PASS | **CONVERGING** | **-0.15** | **4** | 27.0s |

Both rows written to `benchmark/results/scores.csv` (uuids: `ebe294ff`, `940004a5`).

---

## 5. What Each Result Proves

### ✓ pytest bonus mechanism is fixed and working
Both conditions returned `test_passed=True`. The +2 bonus was correctly applied in both cases. The scoring pipeline — solution extraction → pytest → score adjustment → CSV — is intact end-to-end.

### ✓ AttractorFlow genuinely fires with the Agent-tool architecture
`final_regime=CONVERGING` with λ=-0.15 is concrete proof that:
- The orchestrator called `attractorflow_record_state` at least 3 times (PhaseSpaceMonitor minimum)
- The MCP layer was active and receiving data
- The classifier ran and returned a meaningful regime

This was impossible in Round 1. Every Round 1 attractor trial returned `UNKNOWN` because `claude -p` has no MCP access.

### ✓ The two-phase harness decoupling works
`prepare_attractor_trial` and `finalize_attractor_trial` cleanly bracket the Agent spawn. The test suite is pre-written to the temp dir; the agent writes `solution.py` there independently; finalize reads it back and scores it without depending on what the agent said in its text output. The harness does not need to parse AF internals — it just reads the file and runs pytest.

### ✓ Solution quality is equivalent on a well-defined task
Both ralph and attractor produced correct, complete BST implementations. The attractor used a cleaner class structure (`_Node` as a private inner class with helper methods like `_find_min`), but both passed all 8 tests. On a task with a clear correct answer, there's no quality gap — which is expected.

---

## 6. What This Run Does Not Prove

**No AF interventions fired (0 explorer/convergence spawns).** C01 converged on the first attempt — the orchestrator never encountered a STUCK or DIVERGING regime that would trigger subagent spawning. This is the intended behavior for an easy task, but it means the intervention mechanism hasn't been exercised yet.

**No quality advantage demonstrated.** Both conditions score 10/10. C01 is too straightforward to differentiate approaches. A harder task — one where ralph might loop or produce a wrong answer — is needed to see whether AF's trajectory monitoring adds value.

**n=1 per condition.** This is a proof-of-architecture, not a statistical study. The full benchmark (3 reps × 15 tasks) is needed for conclusions.

---

## 7. Next Steps

The architecture is validated. The logical progression:

1. **Complete C01** — run 2 more reps of both conditions to get full 3-rep data on the fixed harness
2. **Extend to C02–C08** — re-run all coding tasks with pytest now working; attractor condition via Agent tool
3. **Add harder tasks** — C01-level tasks can't distinguish conditions; need tasks where convergence isn't guaranteed in step 1
4. **Track AF interventions** — harder tasks should trigger explorer/convergence subagent spawning; those runs will show what AF's actual intervention mechanism does

---

## 8. Solutions Produced

### Ralph output (uuid: ebe294ff)
Single-pass `claude -p` response. Used a separate top-level `Node` class.

```python
class Node:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None

class BinarySearchTree:
    def __init__(self): self.root = None
    def insert(self, value): ...   # recursive, ignores duplicates
    def search(self, value): ...   # recursive bool return
    def delete(self, value): ...   # all 3 cases: leaf, one child, two children
    def inorder(self): ...         # returns sorted list
    def height(self): ...          # returns 0 for empty tree
```

### Attractor output (uuid: 940004a5)
4-step orchestrated response. Used `_Node` as a private inner class with explicit helper methods.

```python
class BinarySearchTree:
    class _Node:
        def __init__(self, value): ...

    def insert(self, value): self.root = self._insert_recursive(self.root, value)
    def _insert_recursive(self, node, value): ...  # returns updated subtree root
    def search(self, value): return self._search_recursive(self.root, value)
    def delete(self, value): self.root = self._delete_recursive(self.root, value)
    def _delete_recursive(self, node, value): ...  # inorder successor for 2-child case
    def _find_min(self, node): ...   # iterative min finder
    def inorder(self): ...
    def height(self): ...
```

Both: 8/8 tests pass. Semantically equivalent. Attractor's version slightly more structured (private helpers, consistent return-value pattern).
