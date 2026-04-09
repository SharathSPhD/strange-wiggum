"""
Leaderboard and statistical report generator.

Reads scores.csv + stats_summary.json and writes results/leaderboard.md.

Usage:
    python -m benchmark.report
    python -m benchmark.report --input results/scores.csv --stats results/stats_summary.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from benchmark.config import (
    CONDITION_LABELS,
    LEADERBOARD_MD,
    SCORES_CSV,
    STATS_JSON,
)


# ── Formatting helpers ─────────────────────────────────────────────────────


def _fmt_p(p: float) -> str:
    if p < 0.001:
        return "< 0.001"
    return f"{p:.3f}"


def _sig_stars(p: float, bonferroni: bool = False) -> str:
    thresh = 0.0167 if bonferroni else 0.05
    if p < thresh * 0.002:
        return "***"
    if p < thresh * 0.02:
        return "**"
    if p < thresh:
        return "*"
    return "ns"


def _rank_medal(rank: int) -> str:
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")


# ── Section builders ───────────────────────────────────────────────────────


def _header(n_tasks: int, n_reps: int, n_trials: int) -> str:
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return f"""# Ralph vs AttractorFlow — Benchmark Leaderboard

> Generated: {ts}
> Tasks: {n_tasks} · Reps: {n_reps} · Conditions: 3 · Total trials: {n_trials}
> Quality score: 0–10 (LLM-judged, blinded) | Coding tasks: +2 bonus for passing tests (cap 10)

---
"""


def _overall_leaderboard(descs: list[dict], pairwise: list[dict], ralph_ref: str = "ralph") -> str:
    lines = ["## Overall Leaderboard\n"]
    header = "| Rank | Condition | Quality μ | σ | 95% CI | vs. Ralph p | Cohen's d |"
    sep =    "|------|-----------|-----------|---|--------|-------------|-----------|"
    lines += [header, sep]

    # Build lookup: (cond_a, cond_b) → p_bonferroni, cohen_d
    pw_lookup: dict[tuple, dict] = {}
    for pw in pairwise:
        pw_lookup[(pw["condition_a"], pw["condition_b"])] = pw
        pw_lookup[(pw["condition_b"], pw["condition_a"])] = {
            **pw,
            "mean_diff": -pw["mean_diff"],
            "cohen_d": -pw["cohen_d"],
        }

    for rank, d in enumerate(descs, 1):
        cond = d["condition"]
        label = d["label"]
        ci = f"[{d['ci_95_lo']:.2f}, {d['ci_95_hi']:.2f}]"

        if cond == ralph_ref:
            vs_p = "—"
            vs_d = "—"
        else:
            pw = pw_lookup.get((cond, ralph_ref)) or pw_lookup.get((ralph_ref, cond))
            if pw:
                p_bon = pw["p_bonferroni"]
                d_val = pw.get("cohen_d", 0.0)
                stars = _sig_stars(p_bon, bonferroni=True)
                vs_p = f"{_fmt_p(p_bon)} {stars}"
                vs_d = f"{d_val:+.2f}"
            else:
                vs_p = "N/A"
                vs_d = "N/A"

        medal = _rank_medal(rank)
        lines.append(
            f"| {medal} | **{label}** | {d['mean']:.2f} | {d['sd']:.2f} | {ci} | {vs_p} | {vs_d} |"
        )

    lines.append("")
    lines.append("> \\* p < 0.0167 (Bonferroni-adjusted α for 3 comparisons), \\*\\* p < 0.0003, \\*\\*\\* p < 0.00003")
    lines.append("")
    return "\n".join(lines) + "\n"


def _pairwise_table(pairwise: list[dict]) -> str:
    lines = ["## Pairwise Comparisons (Bonferroni-corrected)\n"]
    header = "| Comparison | Δμ | 95% CI | t | p (raw) | p (Bonf.) | Cohen's d | Sig. |"
    sep =    "|------------|-----|--------|---|---------|-----------|-----------|------|"
    lines += [header, sep]
    for pw in pairwise:
        a_lbl = CONDITION_LABELS.get(pw["condition_a"], pw["condition_a"])
        b_lbl = CONDITION_LABELS.get(pw["condition_b"], pw["condition_b"])
        ci = f"[{pw['ci_95_lo']:.2f}, {pw['ci_95_hi']:.2f}]"
        sig = "✓" if pw["significant"] else "✗"
        lines.append(
            f"| {a_lbl} vs {b_lbl} | {pw['mean_diff']:+.2f} | {ci} | "
            f"{pw['t_stat']:.2f} | {_fmt_p(pw['p_value'])} | "
            f"{_fmt_p(pw['p_bonferroni'])} | {pw['cohen_d']:+.2f} | {sig} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def _anova_section(anova: dict) -> str:
    if "error" in anova:
        return f"## ANOVA\n\nERROR: {anova['error']}\n\n"
    lines = ["## Repeated-Measures ANOVA\n"]
    lines.append(
        f"**F({anova['df1']:.0f}, {anova['df2']:.0f}) = {anova['F']:.3f}**, "
        f"p = {_fmt_p(anova['p_value'])}, partial η² = {anova['partial_eta_sq']:.3f}"
    )
    eps = anova.get("GG_epsilon", float("nan"))
    p_gg = anova.get("p_GG_corrected", float("nan"))
    if not (eps != eps):  # not NaN
        lines.append(
            f"\nGreehouse-Geisser correction: ε = {eps:.3f}, p (corrected) = {_fmt_p(p_gg)}"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def _subgroup_table(subgroup: dict) -> str:
    if not subgroup:
        return ""
    lines = ["## Subgroup Analysis (Coding vs Analysis Tasks)\n"]
    header = "| Category | F | p | partial η² | N tasks |"
    sep =    "|----------|---|---|------------|---------|"
    lines += [header, sep]
    for cat, res in subgroup.items():
        if "error" in res:
            lines.append(f"| {cat} | — | — | — | — |")
        else:
            lines.append(
                f"| {cat.capitalize()} | {res['F']:.3f} | {_fmt_p(res['p_value'])} | "
                f"{res['partial_eta_sq']:.3f} | {res['n_tasks']} |"
            )
    lines.append("")
    return "\n".join(lines) + "\n"


def _efficiency_table(df: pd.DataFrame) -> str:
    lines = ["## Efficiency Metrics\n"]
    header = "| Condition | Avg Iterations | Avg Tokens | Avg AF Interventions | Avg Time (s) |"
    sep =    "|-----------|----------------|------------|----------------------|--------------|"
    lines += [header, sep]
    for cond, g in df.groupby("condition"):
        label = CONDITION_LABELS.get(cond, cond)
        iters = g["iterations"].mean() if "iterations" in g else float("nan")
        tokens = g["tokens"].mean() if "tokens" in g else float("nan")
        af_int = g["af_interventions"].mean() if "af_interventions" in g else float("nan")
        elapsed = g["elapsed"].mean() if "elapsed" in g else float("nan")
        lines.append(
            f"| {label} | {iters:.1f} | {tokens:.0f} | "
            f"{'N/A' if cond == 'ralph' else f'{af_int:.1f}'} | {elapsed:.1f} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def _regime_table(df: pd.DataFrame) -> str:
    af_df = df[df["condition"].isin(["attractor", "combined"])]
    if "final_regime" not in af_df.columns or af_df.empty:
        return ""
    lines = ["## AttractorFlow Regime Distribution\n"]
    header = "| Final Regime | % of Trials | Avg Quality |"
    sep =    "|--------------|-------------|-------------|"
    lines += [header, sep]
    regime_groups = af_df.groupby("final_regime")
    total = len(af_df)
    for regime, g in regime_groups:
        pct = len(g) / total * 100
        avg_q = g["quality_score"].mean()
        lines.append(f"| {regime} | {pct:.1f}% | {avg_q:.2f} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def _task_breakdown(df: pd.DataFrame) -> str:
    lines = ["## Per-Task Results\n"]
    header = "| Task | Category | Ralph μ | AttractorFlow μ | Combined μ | Best |"
    sep =    "|------|----------|---------|-----------------|------------|------|"
    lines += [header, sep]

    df = df.copy()
    df["category"] = df["task_id"].apply(lambda x: "coding" if str(x).startswith("C") else "analysis")

    for tid in sorted(df["task_id"].unique()):
        tdf = df[df["task_id"] == tid]
        cat = tdf["category"].iloc[0]
        means = {}
        for cond, g in tdf.groupby("condition"):
            means[cond] = g["quality_score"].mean()
        r_mu = f"{means.get('ralph', float('nan')):.2f}"
        a_mu = f"{means.get('attractor', float('nan')):.2f}"
        c_mu = f"{means.get('combined', float('nan')):.2f}"
        best_cond = max(means, key=means.get) if means else "—"
        best_lbl = CONDITION_LABELS.get(best_cond, best_cond)
        lines.append(f"| {tid} | {cat} | {r_mu} | {a_mu} | {c_mu} | {best_lbl} |")

    lines.append("")
    return "\n".join(lines) + "\n"


def _icc_section(icc: dict) -> str:
    if "error" in icc:
        return f"> **Judge consistency (ICC):** {icc['error']}\n\n"
    return (
        f"> **Judge consistency (ICC2):** {icc['icc']:.3f}  "
        f"95%CI [{icc['ci_95_lo']:.3f}, {icc['ci_95_hi']:.3f}]  "
        f"p = {_fmt_p(icc['p_value'])}\n\n"
    )


def _lambda_section(corr: dict) -> str:
    if not corr or "error" in corr:
        return ""
    return (
        f"> **λ vs Quality:** Pearson r = {corr['pearson_r']:.3f}, "
        f"p = {_fmt_p(corr['p_value'])}, n = {corr['n']}\n\n"
    )


def _power_section(power: dict) -> str:
    if "error" in power:
        return ""
    return (
        f"> **Post-hoc power:** N/condition = {power['n_per_condition']}, "
        f"observed F = {power['observed_F']:.3f}, "
        f"approx. power = {power['power_approx']:.2%}\n\n"
    )


def _normality_section(normality: dict) -> str:
    lines = ["## Normality (Shapiro-Wilk)\n"]
    for cond, res in normality.items():
        label = CONDITION_LABELS.get(cond, cond)
        if "error" in res:
            lines.append(f"- **{label}**: {res['error']}")
        else:
            flag = "" if res["normal"] else " ← **non-normal**"
            lines.append(
                f"- **{label}**: W = {res['W']:.4f}, p = {_fmt_p(res['p_value'])}{flag}"
            )
    lines.append("")
    return "\n".join(lines) + "\n"


def _methodology_footer() -> str:
    return """---

## Methodology

| Parameter | Value |
|-----------|-------|
| Design | Within-subjects (all 3 conditions per task) |
| Tasks | 15 (8 coding + 7 analysis) |
| Reps | 3 per task per condition |
| Total trials | 135 |
| Primary analysis | Repeated-measures ANOVA |
| Sphericity | Mauchly's test; Greenhouse-Geisser correction if violated |
| Post-hoc | Pairwise t-tests, Bonferroni α_adj = 0.0167 |
| Bootstrap | 10,000 iterations, seed = 42 |
| Effect sizes | Cohen's d (pairwise), partial η² (ANOVA) |
| Judge | Claude (temperature=0, blinded outputs) |
| Blinding | UUID-named output files; condition hidden from judge |

*Generated by `benchmark/report.py`*
"""


# ── Main ───────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Generate leaderboard.md from benchmark results")
    parser.add_argument("--input", default=SCORES_CSV)
    parser.add_argument("--stats", default=STATS_JSON)
    parser.add_argument("--output", default=LEADERBOARD_MD)
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"ERROR: {args.input} not found. Run harness.py first."); sys.exit(1)

    df = pd.read_csv(args.input)
    df["quality_score"] = pd.to_numeric(df["quality_score"], errors="coerce")

    # Load stats (compute inline if missing)
    if Path(args.stats).exists():
        stats = json.loads(Path(args.stats).read_text())
    else:
        print(f"WARNING: {args.stats} not found — running stats inline (may be slow)")
        from benchmark.stats import (
            run_descriptives,
            run_icc,
            run_kruskal,
            run_normality,
            run_pairwise,
            run_pearson_lambda_quality,
            run_rm_anova,
            run_subgroup_anova,
            post_hoc_power,
            _load_data,
        )
        df2 = _load_data(args.input)
        descs = run_descriptives(df2)
        anova = run_rm_anova(df2)
        pairwise = run_pairwise(df2)
        stats = {
            "descriptives": descs,
            "normality": run_normality(df2),
            "rm_anova": anova,
            "pairwise": pairwise,
            "kruskal_iterations": run_kruskal(df2, "iterations") if "iterations" in df2.columns else {},
            "lambda_quality_correlation": run_pearson_lambda_quality(df2) if "final_lambda" in df2.columns else {},
            "icc": run_icc(df2),
            "subgroup_anova": run_subgroup_anova(df2),
            "power": post_hoc_power(df2.groupby("condition").size().min(), anova.get("F", 0.0)),
            "n_trials": len(df2),
            "n_tasks": df2["task_id"].nunique(),
            "n_conditions": df2["condition"].nunique(),
            "n_reps": df2["rep"].nunique(),
        }

    descs = stats["descriptives"]
    pairwise = stats["pairwise"]
    anova = stats["rm_anova"]
    icc = stats.get("icc", {})
    corr = stats.get("lambda_quality_correlation", {})
    power = stats.get("power", {})
    normality = stats.get("normality", {})
    subgroup = stats.get("subgroup_anova", {})

    n_tasks = stats.get("n_tasks", df["task_id"].nunique())
    n_reps = stats.get("n_reps", df["rep"].nunique())
    n_trials = stats.get("n_trials", len(df))

    # ── Compose report ─────────────────────────────────────────────────────
    sections = [
        _header(n_tasks, n_reps, n_trials),
        _overall_leaderboard(descs, pairwise),
        _anova_section(anova),
        _pairwise_table(pairwise),
        _normality_section(normality),
        _subgroup_table(subgroup),
        _efficiency_table(df),
        _regime_table(df),
        _task_breakdown(df),
        "## Statistical Notes\n\n",
        _icc_section(icc),
        _lambda_section(corr),
        _power_section(power),
        _methodology_footer(),
    ]

    report = "\n".join(sections)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(report)
    print(f"Leaderboard → {args.output}")


if __name__ == "__main__":
    main()
