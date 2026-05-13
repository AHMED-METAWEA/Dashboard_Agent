"""
Dashboard Agent — Chart Selector
Groq-powered chart selection with post-validation and rule-based fallback.
The model DYNAMICALLY decides how many charts to generate based on the data.
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import List, Optional

from config.settings import (
    ALLOWED_CHART_TYPES, GROQ_MAX_TOKENS, GROQ_MODEL,
    GROQ_RETRY_WAIT_SEC, GROQ_TEMPERATURE,
)
from utils.json_parser import extract_json

logger = logging.getLogger(__name__)


@dataclass
class ChartSpec:
    chart_id: str
    chart_type: str
    title: str
    subtitle: str
    x_column: Optional[str]
    y_column: Optional[str]
    color_column: Optional[str]
    aggregation: str
    is_primary: bool
    sort_by: str
    top_n: int


def _build_profile_summary(profile) -> str:
    lines = [f"Dataset: {profile.total_rows} rows, {profile.total_cols} columns",
             f"Domain: {profile.domain}", ""]

    # Describe column types clearly
    lines.append("COLUMNS (use these EXACT names):")
    for col, cp in profile.columns.items():
        detail = f"  - {col} (type={cp.col_type}, dtype={cp.dtype})"
        if cp.col_type == "numeric":
            s = cp.stats
            detail += f" min={s.get('min')}, max={s.get('max')}, mean={s.get('mean', 0):.2f}"
            detail += f" unique_values={len(profile.df[col].dropna().unique())}"
        elif cp.col_type == "categorical":
            top = cp.stats.get("top_10", [])
            vals = ", ".join(f"{t['value']}({t['count']})" for t in top[:5])
            detail += f" unique={cp.stats.get('unique_count')}, values=[{vals}]"
        elif cp.col_type == "datetime":
            detail += f" range={cp.stats.get('min_date')} to {cp.stats.get('max_date')}"
            detail += f" range_days={cp.stats.get('range_days', 0)}"
        lines.append(detail)

    # Provide insight hints
    lines.append("")
    lines.append("DATA CHARACTERISTICS:")
    if profile.datetime_cols:
        lines.append(f"  - Has time dimension: {profile.datetime_cols} → good for trend/time-series charts")
    if profile.categorical_cols:
        for cat in profile.categorical_cols:
            cp = profile.columns[cat]
            n_unique = cp.stats.get("unique_count", 0)
            if n_unique <= 8:
                lines.append(f"  - '{cat}' has {n_unique} categories → great for pie/donut/bar breakdown")
            else:
                lines.append(f"  - '{cat}' has {n_unique} categories → good for top-N bar chart")
    if len(profile.numeric_cols) >= 2:
        lines.append(f"  - Multiple numeric columns: {profile.numeric_cols} → potential for correlation/comparison")

    return "\n".join(lines)


def _build_prompt(profile) -> str:
    summary = _build_profile_summary(profile)
    valid_cols = list(profile.df.columns)

    # Count data characteristics to suggest chart count range
    n_cat = len(profile.categorical_cols)
    n_num = len(profile.numeric_cols)
    n_date = len(profile.datetime_cols)
    n_bool = len(profile.boolean_cols)

    # Calculate a reasonable range
    potential = 0
    if n_date > 0 and n_num > 0:
        potential += min(n_num, 2)  # time series trends
    if n_cat > 0 and n_num > 0:
        potential += min(n_cat * n_num, 4)  # category breakdowns
    if n_cat > 0:
        potential += min(n_cat, 2)  # distribution/pie charts
    if n_num >= 2:
        potential += 1  # scatter/correlation
    if n_num > 0:
        potential += 1  # histogram

    min_suggest = max(3, min(potential, 4))
    max_suggest = max(min_suggest + 1, min(potential, 8))

    return (
        "You are a senior data visualization expert. Given the dataset profile below, "
        "select the BEST set of charts for an executive dashboard.\n\n"
        "CRITICAL RULES:\n"
        f"1. Choose between {min_suggest} and {max_suggest} charts — pick ONLY charts that provide CLEAR, MEANINGFUL insights.\n"
        "2. Do NOT create redundant charts. Each chart must show a DIFFERENT perspective.\n"
        "3. For TIME-SERIES data: use 'line' or 'area' charts with the datetime column as x_column "
        "and a numeric column as y_column. The aggregation should be 'sum' or 'mean' (data will be grouped by date).\n"
        "4. For CATEGORICAL distributions (like payment methods, product types): use 'donut' or 'bar' charts. "
        "Set x_column to the categorical column, y_column to a numeric column (or null for count), "
        "and aggregation to 'count' or 'sum'.\n"
        "5. For NUMERIC distributions: use 'histogram' or 'box'. Set x_column to the numeric column.\n"
        "6. For COMPARISONS across categories: use 'bar' or 'horizontal_bar'.\n"
        "7. For CORRELATIONS between two numerics: use 'scatter' ONLY if both columns have many distinct values (>10 unique). "
        "Do NOT use scatter for columns with few discrete values (e.g., Quantity with values 1-5).\n"
        "8. AVOID pie/donut if the categorical column has more than 8 unique values.\n"
        "9. For grouped analysis: use color_column to split bars/lines by a categorical variable.\n\n"
        "Return ONLY a valid JSON array. No markdown. No explanation. No preamble.\n"
        "Every object in the array must have EXACTLY these keys:\n"
        "{\n"
        '  "chart_id":      string  — unique slug (e.g. \'revenue_by_region\'),\n'
        '  "chart_type":    string  — one of: bar, horizontal_bar, line, area, scatter, '
        'pie, donut, histogram, box, heatmap, treemap, bubble,\n'
        '  "title":         string  — max 7 words, specific and descriptive,\n'
        '  "subtitle":      string  — one sentence explaining what insight this chart reveals,\n'
        '  "x_column":      string  — EXACT column name from the VALID COLUMN NAMES list, or null,\n'
        '  "y_column":      string  — EXACT column name from the VALID COLUMN NAMES list, or null,\n'
        '  "color_column":  string  — EXACT column name for color grouping, or null,\n'
        '  "aggregation":   string  — one of: sum, mean, count, median, max, min, none,\n'
        '  "is_primary":    boolean — true for exactly ONE chart (the most important),\n'
        '  "sort_by":       string  — one of: value_desc, value_asc, label_asc, none,\n'
        '  "top_n":         integer — show only top N categories (0 = show all)\n'
        "}\n\n"
        f"VALID COLUMN NAMES: {json.dumps(valid_cols)}\n\n"
        f"DATASET PROFILE:\n{summary}"
    )


def _call_groq(groq_client, prompt: str) -> list:
    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=GROQ_TEMPERATURE,
        max_tokens=GROQ_MAX_TOKENS,
    )
    raw = response.choices[0].message.content
    return extract_json(raw)


def _validate_charts(raw_charts: list, valid_columns: set, profile=None) -> List[ChartSpec]:
    validated = []
    seen_ids = set()

    for i, c in enumerate(raw_charts):
        if not isinstance(c, dict):
            continue

        chart_type = c.get("chart_type", "")
        if chart_type not in ALLOWED_CHART_TYPES:
            logger.warning(f"Skipping chart: invalid type '{chart_type}'")
            continue

        x_col = c.get("x_column")
        y_col = c.get("y_column")
        color_col = c.get("color_column")

        if x_col and x_col not in valid_columns:
            logger.warning(f"Skipping chart: x_column '{x_col}' not found")
            continue
        if y_col and y_col not in valid_columns:
            logger.warning(f"Skipping chart: y_column '{y_col}' not found")
            continue
        if color_col and color_col not in valid_columns:
            color_col = None

        chart_id = c.get("chart_id", f"chart_{i}")
        if chart_id in seen_ids:
            chart_id = f"{chart_id}_{i}"
        seen_ids.add(chart_id)

        agg = c.get("aggregation", "sum")
        if agg not in ("sum", "mean", "count", "median", "max", "min", "none"):
            agg = "sum"

        sort_by = c.get("sort_by", "none")
        if sort_by not in ("value_desc", "value_asc", "label_asc", "none"):
            sort_by = "none"

        # Post-validation: fix common AI mistakes
        if profile:
            # Fix scatter plots with low-cardinality discrete columns
            if chart_type == "scatter" and x_col and y_col:
                x_unique = len(profile.df[x_col].dropna().unique()) if x_col in profile.df.columns else 0
                y_unique = len(profile.df[y_col].dropna().unique()) if y_col in profile.df.columns else 0
                if x_unique <= 10 or y_unique <= 10:
                    # Convert to a box plot instead — much more informative
                    chart_type = "box"
                    agg = "none"
                    logger.info(f"Converted scatter to box plot for '{x_col}' vs '{y_col}' (low cardinality)")

            # Fix pie/donut with too many categories
            if chart_type in ("pie", "donut") and x_col:
                if x_col in profile.columns:
                    cp = profile.columns[x_col]
                    n_unique = cp.stats.get("unique_count", 0)
                    if n_unique > 12:
                        chart_type = "horizontal_bar"
                        sort_by = "value_desc"
                        if c.get("top_n", 0) == 0:
                            c["top_n"] = 10
                        logger.info(f"Converted pie/donut to horizontal_bar for '{x_col}' ({n_unique} categories)")

            # Fix time series: ensure sort is chronological
            if chart_type in ("line", "area") and x_col:
                if x_col in profile.datetime_cols:
                    sort_by = "label_asc"  # Will be handled by JS date sorting

        validated.append(ChartSpec(
            chart_id=chart_id, chart_type=chart_type,
            title=c.get("title", f"Chart {i+1}")[:60],
            subtitle=c.get("subtitle", "")[:120],
            x_column=x_col, y_column=y_col, color_column=color_col,
            aggregation=agg, is_primary=bool(c.get("is_primary", False)),
            sort_by=sort_by, top_n=int(c.get("top_n", 0)),
        ))

    primary_count = sum(1 for ch in validated if ch.is_primary)
    if primary_count == 0 and validated:
        validated[0].is_primary = True
    elif primary_count > 1:
        first_found = False
        for ch in validated:
            if ch.is_primary:
                if first_found:
                    ch.is_primary = False
                first_found = True

    return validated


def _rule_based_fallback(profile, existing: List[ChartSpec]) -> List[ChartSpec]:
    """Generate smart fallback charts when AI fails or returns too few."""
    fallback = []
    existing_ids = {c.chart_id for c in existing}

    # 1. Monthly revenue/sales trend (aggregated by month)
    if profile.datetime_cols and profile.numeric_cols:
        cid = "monthly_trend"
        if cid not in existing_ids:
            # Pick the best numeric column (prefer revenue/sales/total)
            best_num = profile.numeric_cols[0]
            for col in profile.numeric_cols:
                if any(kw in col.lower() for kw in ["total", "spent", "revenue", "sales", "amount"]):
                    best_num = col
                    break
            fallback.append(ChartSpec(
                chart_id=cid, chart_type="area",
                title=f"Monthly {best_num.replace('_', ' ').title()} Trend",
                subtitle=f"How {best_num.replace('_', ' ')} changes over time",
                x_column=profile.datetime_cols[0], y_column=best_num,
                color_column=None, aggregation="sum", is_primary=not existing,
                sort_by="label_asc", top_n=0,
            ))

    # 2. Top items by category (bar chart)
    if profile.categorical_cols and profile.numeric_cols:
        best_cat = profile.categorical_cols[0]
        best_num = profile.numeric_cols[0]
        for col in profile.numeric_cols:
            if any(kw in col.lower() for kw in ["total", "spent", "revenue", "sales"]):
                best_num = col
                break

        cid = "category_bar"
        if cid not in existing_ids:
            cp = profile.columns[best_cat]
            n_unique = cp.stats.get("unique_count", 0)
            fallback.append(ChartSpec(
                chart_id=cid, chart_type="bar",
                title=f"{best_num.replace('_', ' ').title()} by {best_cat.replace('_', ' ').title()}",
                subtitle=f"Comparison of {best_num.replace('_', ' ')} across {best_cat.replace('_', ' ')} categories",
                x_column=best_cat, y_column=best_num,
                color_column=None, aggregation="sum", is_primary=False,
                sort_by="value_desc", top_n=min(n_unique, 10),
            ))

    # 3. Category distribution (donut chart for low-cardinality)
    if profile.categorical_cols:
        for cat in profile.categorical_cols:
            cp = profile.columns[cat]
            n_unique = cp.stats.get("unique_count", 0)
            if n_unique <= 8:
                cid = f"distribution_{cat.lower().replace(' ', '_')}"
                if cid not in existing_ids:
                    fallback.append(ChartSpec(
                        chart_id=cid, chart_type="donut",
                        title=f"{cat.replace('_', ' ').title()} Distribution",
                        subtitle=f"Proportion of transactions by {cat.replace('_', ' ')}",
                        x_column=cat,
                        y_column=profile.numeric_cols[0] if profile.numeric_cols else None,
                        color_column=None,
                        aggregation="count" if not profile.numeric_cols else "sum",
                        is_primary=False, sort_by="value_desc", top_n=0,
                    ))
                    break

    # 4. Distribution histogram
    if profile.numeric_cols:
        # Pick a meaningful numeric column
        best_num = profile.numeric_cols[0]
        for col in profile.numeric_cols:
            if any(kw in col.lower() for kw in ["total", "spent", "revenue", "price", "amount"]):
                best_num = col
                break

        cid = "value_distribution"
        if cid not in existing_ids:
            fallback.append(ChartSpec(
                chart_id=cid, chart_type="histogram",
                title=f"{best_num.replace('_', ' ').title()} Distribution",
                subtitle=f"Frequency distribution of {best_num.replace('_', ' ')} values",
                x_column=best_num, y_column=None,
                color_column=None, aggregation="count", is_primary=False,
                sort_by="none", top_n=0,
            ))

    # 5. Box plot for numeric by category
    if profile.numeric_cols and profile.categorical_cols:
        best_num = profile.numeric_cols[0]
        for col in profile.numeric_cols:
            if any(kw in col.lower() for kw in ["total", "spent", "price"]):
                best_num = col
                break
        best_cat = profile.categorical_cols[0]

        cid = "box_comparison"
        if cid not in existing_ids:
            fallback.append(ChartSpec(
                chart_id=cid, chart_type="box",
                title=f"{best_num.replace('_', ' ').title()} by {best_cat.replace('_', ' ').title()}",
                subtitle=f"Statistical distribution of {best_num.replace('_', ' ')} across categories",
                x_column=best_cat, y_column=best_num,
                color_column=None, aggregation="none", is_primary=False,
                sort_by="none", top_n=0,
            ))

    return fallback


def select_charts(profile, groq_client) -> List[ChartSpec]:
    valid_columns = set(profile.df.columns)
    prompt = _build_prompt(profile)

    charts = []
    try:
        logger.info("Requesting chart recommendations from Groq...")
        raw = _call_groq(groq_client, prompt)
        if isinstance(raw, list):
            charts = _validate_charts(raw, valid_columns, profile=profile)
            logger.info(f"Groq returned {len(raw)} charts, {len(charts)} passed validation")
    except Exception as e:
        logger.warning(f"Groq chart selection failed: {e}")

    if len(charts) < 3:
        logger.info("Below minimum — retrying Groq with explicit guidance...")
        try:
            time.sleep(GROQ_RETRY_WAIT_SEC)
            retry_prompt = (
                prompt +
                "\n\nIMPORTANT: Only use columns from VALID COLUMN NAMES above. "
                "You MUST return at least 4 charts. Make sure pie/donut charts "
                "have valid x_column and aggregation."
            )
            raw = _call_groq(groq_client, retry_prompt)
            if isinstance(raw, list):
                retry_charts = _validate_charts(raw, valid_columns, profile=profile)
                existing_ids = {c.chart_id for c in charts}
                for rc in retry_charts:
                    if rc.chart_id not in existing_ids:
                        charts.append(rc)
                        existing_ids.add(rc.chart_id)
        except Exception as e:
            logger.warning(f"Groq retry failed: {e}")

    if len(charts) < 3:
        logger.info("Generating rule-based fallback charts...")
        fallback = _rule_based_fallback(profile, charts)
        for fb in fallback:
            if len(charts) >= 6:
                break
            charts.append(fb)

    # Cap at a reasonable max (but let the model decide within range)
    charts = charts[:10]
    logger.info(f"Final chart selection: {len(charts)} charts — {[c.chart_id for c in charts]}")
    return charts
