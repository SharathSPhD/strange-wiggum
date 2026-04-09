"""Benchmark configuration — edit before running."""
import os

# ── Model ──────────────────────────────────────────────────────────────────
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096
TEMPERATURE = 1.0

# ── Execution ──────────────────────────────────────────────────────────────
MAX_ITERATIONS_RALPH = 10      # Ralph loop hard cap
COMPLETION_PROMISE = "TASK COMPLETE"

# ── Reproducibility ────────────────────────────────────────────────────────
SEED = 42

# ── AttractorFlow MCP server (direct Python import path) ──────────────────
ATTRACTORFLOW_MCP_PATH = os.path.expanduser(
    "~/.claude/plugins/cache/attractor-flow/AttractorFlow/1.0.0/attractorflow/mcp-server"
)

# The AF MCP server's uv-managed environment (has sentence_transformers, torch)
ATTRACTORFLOW_SITE_PACKAGES = os.path.expanduser(
    "~/.cache/uv/environments-v2/server-cdf0c9fe3a6afeda/lib/python3.13/site-packages"
)

# AttractorFlow tuning
AF_BUFFER_CAPACITY = 100
AF_WINDOW = 8
AF_CHECK_EVERY_N_STEPS = 3     # regime check frequency

# ── Paths ──────────────────────────────────────────────────────────────────
BENCHMARK_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_DIR = os.path.join(BENCHMARK_DIR, "tasks")
RESULTS_DIR = os.path.join(BENCHMARK_DIR, "results")
RAW_DIR = os.path.join(RESULTS_DIR, "raw")
SCORES_CSV = os.path.join(RESULTS_DIR, "scores.csv")
BLIND_MANIFEST = os.path.join(RESULTS_DIR, "blind_manifest.json")
LEADERBOARD_MD = os.path.join(RESULTS_DIR, "leaderboard.md")
STATS_JSON = os.path.join(RESULTS_DIR, "stats_summary.json")

# ── Latin Square (condition order per rep) ─────────────────────────────────
# Eliminates carry-over effects from condition ordering.
# 3 conditions: R=Ralph, A=AttractorFlow, C=Combined
LATIN_SQUARE = [
    ["ralph", "attractor", "combined"],   # rep 0
    ["attractor", "combined", "ralph"],   # rep 1
    ["combined", "ralph", "attractor"],   # rep 2
]

CONDITION_LABELS = {
    "ralph": "Ralph",
    "attractor": "AttractorFlow",
    "combined": "Ralph + AttractorFlow",
}

# ── CLI runner ─────────────────────────────────────────────────────────────
CLI_MODEL = "claude-haiku-4-5-20251001"  # cheapest model; Sonnet for higher quality
CLI_DELAY_SECONDS = 3.0                  # pause before every CLI call (rate-limit guard)
CLI_MAX_RETRIES = 3                      # attempts with exponential backoff (3s, 6s, 12s)
CLI_TIMEOUT_SECONDS = 120                # per-call hard timeout

# ── Scoring ────────────────────────────────────────────────────────────────
# Coding tasks: LLM rubric score (0–8) + 2-point test-pass bonus (cap at 10)
# Analysis tasks: LLM rubric score (0–10)
TEST_PASS_BONUS = 2
MAX_SCORE = 10
