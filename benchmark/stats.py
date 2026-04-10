"""
Statistical analysis for the Ralph vs AttractorFlow benchmark.

Computes:
- Repeated-measures ANOVA (within-subjects factor: condition)
  - Mauchly's sphericity test; Greenhouse-Geisser correction if violated
- Post-hoc pairwise t-tests (Bonferroni α_adj = 0.0167)
- Effect sizes: Cohen's d (pairwise), partial η²  (ANOVA)
- Kruskal-Wallis on iteration counts (non-parametric)
- Pearson r: final_lambda vs quality_score
- ICC across reps (judge consistency)
- Bootstrap 95% CIs (10,000 iterations, seed=42)
- Subgroup ANOVA: coding vs analysis tasks
- Shapiro-Wilk normality check per condition

Usage:
    python -m benchmark.stats                              # reads results/scores.csv
    python -m benchmark.stats --input path/to/scores.csv
    python -m benchmark.stats --validate                   # shape checks only, no ANOVA
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from benchmark.config import (
    BLIND_MANIFEST,
    CONDITION_LABELS,
    RESULTS_DIR,
    SCORES_CSV,
    SEED,
    STATS_JSON,
)


# ── Helpers ────────────────────────────────────────────────────────────────


def _load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    required = {"task_id", "condition", "rep", "quality_score"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"scores.csv missing columns: {missing}")
    df["quality_score"] = pd.to_numeric(df["quality_score"], errors="coerce")
    df["rep"] = pd.to_numeric(df["rep"], errors="coerce").astype("Int64")
    # Composite subject identifier so each (task, rep) is one "subject"
    df["subject"] = df["task_id"].astype(str) + "_r" + df["rep"].astype(str)
    return df


def _cohen_d(a: np.ndarray, b: np.ndarray) -> float:
    """Pooled-SD Cohen's d for paired differences."""
    diff = a - b
    return float(np.mean(diff) / (np.std(diff, ddof=1) + 1e-12))


def _bootstrap_ci(
    data: np.ndarray,
    statistic=np.mean,
    n_boot: int = 10_000,
    seed: int = SEED,
    ci: float = 0.95,
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    boots = [statistic(rng.choice(data, size=len(data), replace=True)) for _ in range(n_boot)]
    lo = np.percentile(boots, (1 - ci) / 2 * 100)
    hi = np.percentile(boots, (1 + ci) / 2 * 100)
    return float(lo), float(hi)


def _shapiro(arr: np.ndarray) -> tuple[float, float]:
    from scipy import stats
    stat, p = stats.shapiro(arr)
    return float(stat), float(p)


def _bonferroni_threshold(n_comparisons: int, alpha: float = 0.05) -> float:
    return alpha / n_comparisons


# ── Main analyses ──────────────────────────────────────────────────────────


def run_rm_anova(df: pd.DataFrame, dv: str = "quality_score") -> dict:
    """Repeated-measures ANOVA with Mauchly's sphericity test."""
    try:
        import pingouin as pg
    except ImportError:
        return {"error": "pingouin not installed — run: pip install pingouin"}

    result = {}

    # Mauchly's sphericity (pingouin)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        aov = pg.rm_anova(data=df, dv=dv, within="condition", subject="subject", correction=True)

    row = aov.iloc[0]
    result["F"] = float(row.get("F", float("nan")))
    result["df1"] = float(row.get("ddof1", float("nan")))
    result["df2"] = float(row.get("ddof2", float("nan")))
    # pingouin uses p_unc / p_GG_corr / ng2 (underscores, not hyphens; ng2 not np2)
    result["p_value"] = float(row.get("p_unc", row.get("p-unc", float("nan"))))
    result["p_GG_corrected"] = float(row.get("p_GG_corr", row.get("p-GG-corr", float("nan"))))
    result["GG_epsilon"] = float(row.get("eps", float("nan")))
    result["partial_eta_sq"] = float(row.get("ng2", row.get("np2", float("nan"))))

    # Mauchly from sphericity test column
    mauchly_col = [c for c in aov.columns if "spher" in c.lower() or "mauch" in c.lower()]
    result["sphericity_violated"] = bool(row.get("sphericity", True) is False)

    return result


def run_pairwise(df: pd.DataFrame, dv: str = "quality_score") -> list[dict]:
    """Bonferroni-corrected pairwise comparisons between conditions."""
    from scipy import stats

    conditions = df["condition"].unique().tolist()
    pairs = [(a, b) for i, a in enumerate(conditions) for b in conditions[i + 1:]]
    alpha_adj = _bonferroni_threshold(len(pairs))
    results = []

    for cond_a, cond_b in pairs:
        # Align by subject for paired test
        wide = df[df["condition"].isin([cond_a, cond_b])].pivot_table(
            index="subject", columns="condition", values=dv, aggfunc="first"
        ).dropna()
        if wide.shape[0] < 3:
            continue
        a_vals = wide[cond_a].values
        b_vals = wide[cond_b].values
        t_stat, p_val = stats.ttest_rel(a_vals, b_vals)
        d = _cohen_d(a_vals, b_vals)
        ci_lo, ci_hi = _bootstrap_ci(a_vals - b_vals, np.mean)
        results.append({
            "condition_a": cond_a,
            "condition_b": cond_b,
            "mean_a": float(np.mean(a_vals)),
            "mean_b": float(np.mean(b_vals)),
            "mean_diff": float(np.mean(a_vals - b_vals)),
            "ci_95_lo": ci_lo,
            "ci_95_hi": ci_hi,
            "t_stat": float(t_stat),
            "p_value": float(p_val),
            "p_bonferroni": float(min(p_val * len(pairs), 1.0)),
            "significant": bool(p_val < alpha_adj),
            "cohen_d": d,
            "alpha_bonferroni": alpha_adj,
        })

    return results


def run_kruskal(df: pd.DataFrame, dv: str = "iterations") -> dict:
    """Kruskal-Wallis test on a count/non-normal variable."""
    from scipy import stats

    groups = [g[dv].dropna().values for _, g in df.groupby("condition")]
    if len(groups) < 2:
        return {"error": "Need ≥2 conditions"}
    h, p = stats.kruskal(*groups)
    return {"H_stat": float(h), "p_value": float(p), "variable": dv}


def run_pearson_lambda_quality(df: pd.DataFrame) -> dict:
    """Pearson r between final_lambda and quality_score for AF/combined rows."""
    from scipy import stats

    af_df = df[df["condition"].isin(["attractor", "combined"])].dropna(
        subset=["final_lambda", "quality_score"]
    )
    if len(af_df) < 5:
        return {"error": "Insufficient data for λ correlation"}
    r, p = stats.pearsonr(af_df["final_lambda"].values, af_df["quality_score"].values)
    return {"pearson_r": float(r), "p_value": float(p), "n": len(af_df)}


def run_icc(df: pd.DataFrame, dv: str = "quality_score") -> dict:
    """
    Intraclass correlation across reps (judge consistency).
    ICC(2,1) — two-way random effects, single measure, absolute agreement.
    """
    try:
        import pingouin as pg
    except ImportError:
        return {"error": "pingouin not installed"}

    # ICC across reps within (task, condition)
    df2 = df.copy()
    df2["item"] = df2["task_id"] + "_" + df2["condition"]
    icc_df = pg.intraclass_corr(
        data=df2, targets="item", raters="rep", ratings=dv, nan_policy="omit"
    )
    # pingouin uses "ICC(A,1)" or "ICC(1,1)" — find ICC(A,1) for absolute agreement
    icc_type = "ICC(A,1)" if "ICC(A,1)" in icc_df["Type"].values else icc_df["Type"].iloc[0]
    icc21 = icc_df[icc_df["Type"] == icc_type].iloc[0]
    return {
        "ICC_type": icc_type,
        "icc": float(icc21["ICC"]),
        "ci_95_lo": float(icc21["CI95"][0]),
        "ci_95_hi": float(icc21["CI95"][1]),
        "F": float(icc21["F"]),
        "p_value": float(icc21["pval"]),
    }


def run_subgroup_anova(df: pd.DataFrame, manifest_path: str = BLIND_MANIFEST) -> dict:
    """ANOVA separately for coding vs analysis tasks."""
    try:
        import pingouin as pg
    except ImportError:
        return {"error": "pingouin not installed"}

    # Infer task category from task_id prefix (C = coding, A = analysis)
    df = df.copy()
    df["category"] = df["task_id"].apply(lambda x: "coding" if str(x).startswith(("C", "H")) else "analysis")

    results = {}
    for cat, sub_df in df.groupby("category"):
        if sub_df["condition"].nunique() < 2:
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                aov = pg.rm_anova(
                    data=sub_df, dv="quality_score", within="condition",
                    subject="subject", correction=True
                )
            row = aov.iloc[0]
            results[cat] = {
                "F": float(row.get("F", float("nan"))),
                "p_value": float(row.get("p_unc", row.get("p-unc", float("nan")))),
                "partial_eta_sq": float(row.get("ng2", row.get("np2", float("nan")))),
                "n_tasks": sub_df["task_id"].nunique(),
                "n_obs": len(sub_df),
            }
        except Exception as e:
            results[cat] = {"error": str(e)}

    return results


def run_normality(df: pd.DataFrame, dv: str = "quality_score") -> dict:
    """Shapiro-Wilk normality test per condition."""
    results = {}
    for cond, g in df.groupby("condition"):
        arr = g[dv].dropna().values
        if len(arr) < 3:
            results[cond] = {"error": "too few observations"}
            continue
        w, p = _shapiro(arr)
        results[cond] = {"W": w, "p_value": p, "n": len(arr), "normal": p > 0.05}
    return results


def run_descriptives(df: pd.DataFrame, dv: str = "quality_score") -> list[dict]:
    """Per-condition descriptive statistics with bootstrap CIs."""
    rows = []
    for cond, g in df.groupby("condition"):
        arr = g[dv].dropna().values
        ci_lo, ci_hi = _bootstrap_ci(arr)
        rows.append({
            "condition": cond,
            "label": CONDITION_LABELS.get(cond, cond),
            "n": len(arr),
            "mean": float(np.mean(arr)),
            "sd": float(np.std(arr, ddof=1)),
            "median": float(np.median(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "ci_95_lo": ci_lo,
            "ci_95_hi": ci_hi,
        })
    return sorted(rows, key=lambda r: -r["mean"])


# ── Power analysis (post-hoc) ──────────────────────────────────────────────


def post_hoc_power(n_per_condition: int, f_observed: float) -> dict:
    """
    Post-hoc power for repeated-measures ANOVA using Cohen's f.
    Uses scipy to approximate via noncentral F distribution.
    """
    try:
        from scipy import stats
        # For repeated-measures with k=3 conditions, df1=2
        df1 = 2
        df2 = (n_per_condition - 1) * df1
        ncp = f_observed * df1  # approx non-centrality parameter
        f_crit = stats.f.ppf(0.95, df1, df2)
        power = 1 - stats.f.cdf(f_crit, df1, df2, loc=ncp)
        return {
            "n_per_condition": n_per_condition,
            "observed_F": f_observed,
            "df1": df1,
            "df2": df2,
            "power_approx": float(power),
            "alpha": 0.05,
        }
    except Exception as e:
        return {"error": str(e)}


# ── Entry point ────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Benchmark statistical analysis")
    parser.add_argument("--input", default=SCORES_CSV, help="Path to scores.csv")
    parser.add_argument("--validate", action="store_true", help="Shape/type checks only")
    parser.add_argument("--output", default=STATS_JSON, help="Output JSON path")
    args = parser.parse_args()

    csv_path = args.input
    if not Path(csv_path).exists():
        print(f"ERROR: {csv_path} not found. Run harness.py first."); sys.exit(1)

    df = _load_data(csv_path)
    print(f"\nLoaded {len(df)} trials — {df['task_id'].nunique()} tasks, "
          f"{df['condition'].nunique()} conditions, {df['rep'].nunique()} reps")
    print(f"Conditions: {sorted(df['condition'].unique())}")
    print(f"Quality score range: {df['quality_score'].min():.1f} – {df['quality_score'].max():.1f}")

    if args.validate:
        # Shape checks
        expected_conditions = {"ralph", "attractor", "combined"}
        found = set(df["condition"].unique())
        missing_conds = expected_conditions - found
        if missing_conds:
            print(f"  WARNING: Missing conditions: {missing_conds}")
        else:
            print("  OK: All 3 conditions present")
        n_trials = len(df)
        print(f"  Trials: {n_trials} (expected ~135 for full run)")
        print("Validation complete.")
        return

    print("\n── Descriptive Statistics ────────────────────────────────")
    descs = run_descriptives(df)
    for d in descs:
        print(f"  {d['label']:25s} μ={d['mean']:.2f} σ={d['sd']:.2f} "
              f"95%CI=[{d['ci_95_lo']:.2f},{d['ci_95_hi']:.2f}] n={d['n']}")

    print("\n── Shapiro-Wilk Normality ────────────────────────────────")
    normality = run_normality(df)
    for cond, res in normality.items():
        if "error" not in res:
            flag = "" if res["normal"] else " [NON-NORMAL]"
            print(f"  {CONDITION_LABELS.get(cond, cond):25s} W={res['W']:.4f} p={res['p_value']:.4f}{flag}")

    print("\n── Repeated-Measures ANOVA ───────────────────────────────")
    anova = run_rm_anova(df)
    if "error" in anova:
        print(f"  ERROR: {anova['error']}")
    else:
        print(f"  F({anova['df1']:.0f},{anova['df2']:.0f}) = {anova['F']:.3f}, "
              f"p = {anova['p_value']:.4f}, partial η² = {anova['partial_eta_sq']:.3f}")
        if not np.isnan(anova.get("GG_epsilon", float("nan"))):
            print(f"  Greenhouse-Geisser ε = {anova['GG_epsilon']:.3f}, "
                  f"p(corrected) = {anova['p_GG_corrected']:.4f}")

    print("\n── Pairwise Post-Hoc (Bonferroni α=0.0167) ─────────────")
    pairwise = run_pairwise(df)
    for pw in pairwise:
        sig = "✓" if pw["significant"] else "✗"
        a_lbl = CONDITION_LABELS.get(pw["condition_a"], pw["condition_a"])
        b_lbl = CONDITION_LABELS.get(pw["condition_b"], pw["condition_b"])
        print(f"  {sig} {a_lbl} vs {b_lbl}:")
        print(f"      Δμ = {pw['mean_diff']:+.2f}  95%CI=[{pw['ci_95_lo']:.2f},{pw['ci_95_hi']:.2f}]  "
              f"p_bonf={pw['p_bonferroni']:.4f}  d={pw['cohen_d']:.2f}")

    print("\n── Kruskal-Wallis (iterations) ───────────────────────────")
    if "iterations" in df.columns:
        kw = run_kruskal(df, "iterations")
        if "error" not in kw:
            print(f"  H = {kw['H_stat']:.3f}, p = {kw['p_value']:.4f}")
    else:
        print("  [No 'iterations' column found]")

    print("\n── λ vs Quality Correlation ──────────────────────────────")
    if "final_lambda" in df.columns:
        corr = run_pearson_lambda_quality(df)
        if "error" not in corr:
            print(f"  r = {corr['pearson_r']:.3f}, p = {corr['p_value']:.4f}, n = {corr['n']}")
    else:
        print("  [No 'final_lambda' column found]")

    print("\n── ICC (judge consistency across reps) ───────────────────")
    icc = run_icc(df)
    if "error" not in icc:
        print(f"  ICC2 = {icc['icc']:.3f}  95%CI=[{icc['ci_95_lo']:.3f},{icc['ci_95_hi']:.3f}]  "
              f"p = {icc['p_value']:.4f}")
    else:
        print(f"  {icc['error']}")

    print("\n── Subgroup ANOVA (coding vs analysis) ───────────────────")
    subgroup = run_subgroup_anova(df)
    for cat, res in subgroup.items():
        if "error" not in res:
            print(f"  {cat:10s}: F = {res['F']:.3f}, p = {res['p_value']:.4f}, "
                  f"η² = {res['partial_eta_sq']:.3f}  (n_tasks={res['n_tasks']})")

    print("\n── Post-Hoc Power ────────────────────────────────────────")
    n_per = df.groupby("condition").size().min()
    f_val = anova.get("F", 0.0) if "error" not in anova else 0.0
    power = post_hoc_power(n_per, f_val)
    if "error" not in power:
        print(f"  N/condition={power['n_per_condition']}, "
              f"observed F={power['observed_F']:.3f}, "
              f"approx power={power['power_approx']:.3f}")

    # ── Save JSON summary ──────────────────────────────────────────────────
    summary = {
        "descriptives": descs,
        "normality": normality,
        "rm_anova": anova,
        "pairwise": pairwise,
        "kruskal_iterations": kw if "iterations" in df.columns else {},
        "lambda_quality_correlation": corr if "final_lambda" in df.columns else {},
        "icc": icc,
        "subgroup_anova": subgroup,
        "power": power,
        "n_trials": len(df),
        "n_tasks": df["task_id"].nunique(),
        "n_conditions": df["condition"].nunique(),
        "n_reps": df["rep"].nunique(),
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nStats saved → {args.output}")
    print(f"Next: python -m benchmark.report")


if __name__ == "__main__":
    main()
