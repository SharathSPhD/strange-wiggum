# Agent Wars: Ralph Wiggum vs AttractorFlow

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live%20Presentation-00ff41?style=for-the-badge&logo=github)](https://sharathsphd.github.io/strange-wiggum/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

> A rigorous benchmark duel between two Claude Code orchestration strategies — Ralph Wiggum's brute-force iterative CLI loop vs AttractorFlow's Lyapunov-guided dynamical systems orchestrator.

## Live Presentation

**[sharathsphd.github.io/strange-wiggum](https://sharathsphd.github.io/strange-wiggum/)**

Retro pixel-art presentation with canvas battle animation, live charts, per-task scoreboard, and statistical analysis.

The battle GIF (`docs/agent-wars-battle.gif`) is generated from [`scripts/generate_battle_gif.py`](scripts/generate_battle_gif.py) — ready for LinkedIn posts.

## Results (38 trials · 6 tasks · 2 conditions)

| Condition | Quality μ | σ | Avg Tokens | Avg Time |
|-----------|-----------|---|------------|----------|
| **AttractorFlow** | **9.63** | **0.60** | **601** | 80.4 s |
| Ralph Wiggum | 9.42 | 1.22 | 2,146 | 82.8 s |

- **Not statistically significant**: F(1,18)=0.520, p=0.480, Cohen's d=0.17
- **AttractorFlow uses 72% fewer tokens** at comparable quality
- **AttractorFlow is more consistent**: σ=0.60 vs Ralph's σ=1.22
- **Discriminating task (H02 — Pratt Parser)**: AF=10.00, Ralph=8.75

## Repository Structure

```
benchmark/
├── tasks/          # 6 task specs (coding + analysis)
├── conditions/     # ralph.py + attractor.py runners
├── judge/          # LLM judge (Claude Sonnet 4.6, blinded)
├── results/
│   ├── scores.csv  # All 38 trial scores
│   └── leaderboard.md
├── config.py       # Model + parameter settings
├── harness.py      # Trial orchestration (Ralph condition)
├── agent_harness.py # Trial orchestration (AF condition)
├── stats.py        # Repeated-measures ANOVA + bootstrap CIs
└── report.py       # Leaderboard generator
docs/
├── index.html               # GitHub Pages presentation
├── agent-wars-battle.gif    # Standalone battle animation
└── data/                    # Live data for charts (scores.csv, stats_summary.json)
scripts/
└── generate_battle_gif.py   # Regenerate battle GIF with Pillow
```

## Methodology

| Parameter | Value |
|-----------|-------|
| Design | Within-subjects, Latin-square condition ordering |
| Conditions | Ralph Wiggum loop + AttractorFlow orchestrator |
| Tasks | 6 (5 coding, 1 analysis) |
| Reps | 4 per task per condition (38 total trials) |
| Primary analysis | Repeated-measures ANOVA (pingouin) |
| Post-hoc | Pairwise t-tests, Bonferroni α=0.05 |
| Bootstrap | 10,000 iterations, seed=42 |
| Effect sizes | Cohen's d (pairwise), partial η² (ANOVA) |
| Judge | Claude Sonnet 4.6, temperature=0, blinded UUID outputs |
| Ralph model | claude-haiku-4-5-20251001, max 10 iterations |
| AF model | claude-haiku-4-5-20251001, attractor-flow:attractor-orchestrator |

## Quick Start

```bash
# 1. Clone and set up environment
git clone https://github.com/SharathSPhD/strange-wiggum
cd strange-wiggum
uv venv .venv313 --python 3.13 && source .venv313/bin/activate
pip install -r requirements.txt

# 2. Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# 3. Install AttractorFlow plugin
claude plugin install attractor-flow

# 4. Run a single trial (both conditions, 1 rep)
python -m benchmark.harness --tasks H02 --conditions ralph --reps 1

# 5. Generate stats and leaderboard
python -m benchmark.stats && python -m benchmark.report

# 6. Regenerate battle GIF
python scripts/generate_battle_gif.py
```

## Adapting for Your Own Benchmark

1. **Add tasks** in `benchmark/tasks/coding/` or `benchmark/tasks/analysis/`  
   Format: Markdown spec + fenced Python test suite

2. **Define conditions** in `benchmark/conditions/`  
   `ralph.py` — any iterative CLI loop pattern  
   `attractor.py` — any orchestrator/MCP pattern

3. **Adjust config** in `benchmark/config.py`: model, max iterations, scoring bonuses

4. **Customize the judge rubric** in `benchmark/judge/rubric.md` for your domain

## License

MIT — see [LICENSE](LICENSE)
