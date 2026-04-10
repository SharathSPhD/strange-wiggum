# ⚔ Agent Wars: Ralph Wiggum vs AttractorFlow

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live%20Presentation-00ff41?style=for-the-badge&logo=github)](https://sharathsphd.github.io/strange-wiggum/)

> A rigorous benchmark duel between two Claude Code orchestration strategies — Ralph Wiggum's brute-force iterative CLI loop vs AttractorFlow's Lyapunov-guided dynamical systems orchestrator.

## 🎮 Live Presentation

👉 **[sharathsphd.github.io/strange-wiggum](https://sharathsphd.github.io/strange-wiggum/)**

Retro pixel-art presentation with live charts, per-task scoreboard, statistical analysis, and the full benchmark story.

## 📊 Results (38 trials · 6 tasks · 2 conditions)

| Condition | Quality μ | σ | Avg Tokens | Winner |
|-----------|-----------|---|------------|--------|
| **AttractorFlow** | **9.63** | **0.60** | **601** | 🌀 |
| Ralph Wiggum | 9.42 | 1.22 | 2,146 | |

- **Not statistically significant**: F(1,18)=0.520, p=0.480, Cohen's d=0.17
- **AttractorFlow uses 72% fewer tokens** at comparable quality
- **AttractorFlow is more consistent**: σ=0.60 vs Ralph's σ=1.22
- **Discriminating task (H02 — Pratt Parser)**: AF=10.00, Ralph=8.75

## 📁 Repository Structure

```
benchmark/
├── tasks/          # 6 task specs (coding + analysis)
├── conditions/     # ralph.py + attractor.py runners
├── judge/          # LLM judge (Claude Sonnet 4.6, blinded)
├── results/
│   ├── scores.csv  # All 38 trial scores
│   └── leaderboard.md
├── harness.py      # Trial orchestration
├── stats.py        # Statistical analysis
└── report.py       # Leaderboard generator
docs/
├── index.html      # GitHub Pages presentation
└── data/           # Live data for charts
```

## 🔬 Methodology

- **Design**: Within-subjects, Latin-square condition ordering
- **Judge**: Claude Sonnet 4.6 at temperature=0, blinded UUID outputs
- **Stats**: Repeated-measures ANOVA, Bonferroni correction, bootstrap 95% CIs
- **Ralph**: `claude -p` CLI subprocess loop, max 10 iterations, Haiku 4.5
- **AttractorFlow**: `attractor-flow:attractor-orchestrator` Agent with MCP tools (Lyapunov exponent monitoring, explorer/convergence subagents), Haiku 4.5

## 🚀 Run It Yourself

```bash
# Install dependencies
uv venv .venv313 --python 3.13 && source .venv313/bin/activate
pip install -r requirements.txt

# Run a single trial
python -m benchmark.harness --tasks H02 --conditions ralph --reps 1

# Generate stats + report
python -m benchmark.stats && python -m benchmark.report
```

## 📄 License

MIT © 2026 Strange Wiggum Benchmark
