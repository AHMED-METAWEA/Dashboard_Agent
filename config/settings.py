"""
Dashboard Agent — Central Configuration
All constants, Groq model config, and thresholds.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Groq LLM Configuration ────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_TEMPERATURE = 0.2
GROQ_MAX_TOKENS = 2048
GROQ_RETRY_WAIT_SEC = 10
GROQ_MAX_RETRIES = 3

# ── Data Loading Limits ───────────────────────────────────────────────
MAX_UPLOAD_MB = 200

# ── Sampling Configuration ────────────────────────────────────────────
SAMPLE_THRESHOLD = 100_000   # rows — above this, sample for visualization
SAMPLE_SIZE = 50_000         # rows — visualization sample size

# ── Chart Configuration ──────────────────────────────────────────────
MIN_CHARTS = 6
MAX_CHARTS = 10

# ── KPI Configuration ────────────────────────────────────────────────
MIN_KPIS = 4
MAX_KPIS = 6

# ── Output Configuration ─────────────────────────────────────────────
OUTPUT_FILE = "dashboard_output.html"
PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.26.0.min.js"
DEFAULT_THEME = "dark"   # "dark" or "light"

# ── Allowed Chart Types ──────────────────────────────────────────────
ALLOWED_CHART_TYPES = [
    "bar", "horizontal_bar", "line", "area", "scatter",
    "pie", "donut", "histogram", "box", "heatmap",
    "treemap", "bubble",
]

# ── Column Classification Thresholds ─────────────────────────────────
CATEGORICAL_MAX_UNIQUE = 50
CATEGORICAL_MAX_RATIO = 0.05
NUMERIC_MIN_NON_NULL_RATIO = 0.80

# ── KPI Keyword Mappings ─────────────────────────────────────────────
SUM_KEYWORDS = [
    "revenue", "sales", "amount", "total", "price",
    "cost", "profit", "income", "spend", "expense",
    "payment", "budget", "earning", "fee", "wage",
]
MEAN_KEYWORDS = [
    "rate", "score", "pct", "percent", "ratio",
    "avg", "average", "index", "rating", "grade",
    "satisfaction", "nps", "churn",
]
COUNT_KEYWORDS = [
    "id", "order", "transaction", "ticket", "case",
    "record", "count", "number", "qty", "quantity",
]
