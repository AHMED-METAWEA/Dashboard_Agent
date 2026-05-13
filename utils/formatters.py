"""
Dashboard Agent — Number Formatters
Provides K/M/B abbreviations, percentage formatting, and currency auto-detection.
"""

import re
import math
from typing import Optional


# ── Currency keywords for auto-detection ──────────────────────────────
CURRENCY_KEYWORDS = [
    "revenue", "sales", "amount", "total", "price", "cost", "profit",
    "income", "spend", "expense", "payment", "budget", "earning",
    "fee", "wage", "salary", "balance", "money", "fund", "capital",
    "value", "worth", "dollar", "usd", "eur", "gbp",
]

PERCENTAGE_KEYWORDS = [
    "rate", "pct", "percent", "ratio", "share", "margin",
    "growth", "churn", "conversion", "retention",
]


def format_number(
    value: float,
    column_name: str = "",
    aggregation: str = "sum",
    force_currency: bool = False,
    force_percentage: bool = False,
    decimal_places: int = 1,
) -> str:
    """
    Format a numeric value into a human-readable string.

    Auto-detects whether to apply currency ($) or percentage (%) formatting
    based on the column name. Falls back to K/M/B abbreviations for large numbers.

    Args:
        value: The numeric value to format.
        column_name: Column name for context-based formatting detection.
        aggregation: Aggregation type (sum, mean, count) for formatting hints.
        force_currency: If True, always format as currency.
        force_percentage: If True, always format as percentage.
        decimal_places: Number of decimal places for formatted output.

    Returns:
        Human-readable formatted string.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"

    col_lower = column_name.lower().replace("_", " ").replace("-", " ")

    is_currency = force_currency or any(kw in col_lower for kw in CURRENCY_KEYWORDS)
    is_percentage = force_percentage or any(kw in col_lower for kw in PERCENTAGE_KEYWORDS)

    if is_percentage and not is_currency:
        return _format_percentage(value, decimal_places)

    if is_currency:
        return _format_currency(value, decimal_places)

    if aggregation == "count":
        return _format_count(value)

    return _format_abbreviated(value, decimal_places)


def _format_currency(value: float, decimals: int = 1) -> str:
    """Format as USD currency with K/M/B abbreviation."""
    prefix = "$"
    if value < 0:
        prefix = "-$"
        value = abs(value)

    if value >= 1_000_000_000:
        return f"{prefix}{value / 1_000_000_000:.{decimals}f}B"
    elif value >= 1_000_000:
        return f"{prefix}{value / 1_000_000:.{decimals}f}M"
    elif value >= 1_000:
        return f"{prefix}{value / 1_000:.{decimals}f}K"
    elif value >= 1:
        return f"{prefix}{value:,.{max(0, decimals)}f}"
    else:
        return f"{prefix}{value:.2f}"


def _format_percentage(value: float, decimals: int = 1) -> str:
    """Format as a percentage."""
    if abs(value) > 1 and abs(value) <= 100:
        return f"{value:.{decimals}f}%"
    elif abs(value) <= 1:
        return f"{value * 100:.{decimals}f}%"
    else:
        return f"{value:,.{decimals}f}%"


def _format_count(value: float) -> str:
    """Format an integer count with comma separators."""
    if value == int(value):
        return f"{int(value):,}"
    return f"{value:,.0f}"


def _format_abbreviated(value: float, decimals: int = 1) -> str:
    """Format a number with K/M/B abbreviation."""
    negative = value < 0
    abs_val = abs(value)

    if abs_val >= 1_000_000_000:
        formatted = f"{abs_val / 1_000_000_000:.{decimals}f}B"
    elif abs_val >= 1_000_000:
        formatted = f"{abs_val / 1_000_000:.{decimals}f}M"
    elif abs_val >= 10_000:
        formatted = f"{abs_val / 1_000:.{decimals}f}K"
    elif abs_val >= 1:
        formatted = f"{abs_val:,.{decimals}f}"
    elif abs_val == 0:
        formatted = "0"
    else:
        formatted = f"{abs_val:.{max(2, decimals)}f}"

    return f"-{formatted}" if negative else formatted


def format_delta(delta_pct: Optional[float], direction: Optional[str] = None) -> str:
    """
    Format a period-over-period delta percentage with direction arrow.

    Args:
        delta_pct: Percentage change value.
        direction: 'up' or 'down' (auto-detected if None).

    Returns:
        Formatted string like '▲ 12.3%' or '▼ 5.1%'.
    """
    if delta_pct is None:
        return ""

    if direction is None:
        direction = "up" if delta_pct >= 0 else "down"

    arrow = "▲" if direction == "up" else "▼"
    color_class = "delta-up" if direction == "up" else "delta-down"

    return f'<span class="{color_class}">{arrow} {abs(delta_pct):.1f}%</span>'


def detect_column_format(column_name: str) -> str:
    """
    Detect the likely format type for a column based on its name.

    Returns:
        One of: 'currency', 'percentage', 'count', 'number'
    """
    col_lower = column_name.lower().replace("_", " ").replace("-", " ")

    if any(kw in col_lower for kw in CURRENCY_KEYWORDS):
        return "currency"
    if any(kw in col_lower for kw in PERCENTAGE_KEYWORDS):
        return "percentage"
    if any(kw in col_lower for kw in ["id", "count", "number", "qty", "quantity"]):
        return "count"
    return "number"
