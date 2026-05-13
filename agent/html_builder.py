"""
Dashboard Agent — HTML Builder
Assembles the final self-contained HTML dashboard file using Plotly and Jinja2.
"""

import json
import logging
import math
from typing import List

import numpy as np
import pandas as pd
from jinja2 import Template

from config.settings import DEFAULT_THEME, OUTPUT_FILE, PLOTLY_CDN, SAMPLE_THRESHOLD, SAMPLE_SIZE
from agent.html_template import DASHBOARD_TEMPLATE

logger = logging.getLogger(__name__)


def _safe_value(v):
    if v is None:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v) if not math.isnan(v) else None
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def _df_to_records(df: pd.DataFrame) -> list:
    records = []
    cols = list(df.columns)
    for _, row in df.iterrows():
        rec = {}
        for c in cols:
            val = row[c]
            if pd.api.types.is_datetime64_any_dtype(df[c]):
                rec[c] = val.isoformat() if pd.notna(val) else None
            else:
                rec[c] = _safe_value(val)
        records.append(rec)
    return records


def _build_filters(profile) -> list:
    filters = []
    for col in profile.categorical_cols[:6]:
        cp = profile.columns[col]
        top = cp.stats.get("top_10", [])
        options = [t["value"] for t in top]
        if cp.stats.get("unique_count", 0) <= 30:
            all_vals = sorted(profile.df[col].dropna().unique().astype(str).tolist())
            options = all_vals
        filters.append({
            "id": col.replace(" ", "_").replace(".", "_"),
            "column": col,
            "label": col.replace("_", " ").title(),
            "type": "select",
            "options": options[:30],
        })

    for col in profile.datetime_cols[:2]:
        cp = profile.columns[col]
        min_d = cp.stats.get("min_date", "")
        max_d = cp.stats.get("max_date", "")
        if min_d:
            min_d = str(min_d)[:10]
        if max_d:
            max_d = str(max_d)[:10]
        filters.append({
            "id": col.replace(" ", "_").replace(".", "_"),
            "column": col,
            "label": col.replace("_", " ").title(),
            "type": "date_range",
            "min": min_d,
            "max": max_d,
        })

    for col in profile.numeric_cols[:3]:
        cp = profile.columns[col]
        mn = cp.stats.get("min", 0)
        mx = cp.stats.get("max", 100)
        rng = mx - mn
        if rng == 0:
            continue
        step = round(rng / 100, 2) if rng < 1000 else round(rng / 100, 0)
        if step == 0:
            step = 1
        filters.append({
            "id": col.replace(" ", "_").replace(".", "_"),
            "column": col,
            "label": col.replace("_", " ").title(),
            "type": "range",
            "min": round(mn, 2),
            "max": round(mx, 2),
            "step": step,
        })

    return filters


def _build_kpi_configs(kpis) -> list:
    configs = []
    for k in kpis:
        prefix = ""
        suffix = ""
        col_lower = k.source_column.lower()
        currency_kw = ["revenue", "sales", "amount", "total", "price", "cost", "profit", "income"]
        pct_kw = ["rate", "pct", "percent", "ratio"]
        if any(kw in col_lower for kw in currency_kw):
            prefix = "$"
        elif any(kw in col_lower for kw in pct_kw):
            suffix = "%"
        configs.append({
            "source": k.source_column,
            "agg": k.js_aggregation,
            "prefix": prefix,
            "suffix": suffix,
        })
    return configs


def _build_chart_configs(charts) -> list:
    configs = []
    for c in charts:
        configs.append({
            "chart_id": c.chart_id,
            "chart_type": c.chart_type,
            "title": c.title,
            "subtitle": c.subtitle,
            "x_column": c.x_column,
            "y_column": c.y_column,
            "color_column": c.color_column,
            "aggregation": c.aggregation,
            "is_primary": c.is_primary,
            "sort_by": c.sort_by,
            "top_n": c.top_n,
        })
    return configs


def _build_kpi_template_data(kpis) -> list:
    data = []
    for k in kpis:
        data.append({
            "label": k.label,
            "formatted_value": k.formatted_value,
            "delta_pct": k.delta_pct,
            "delta_direction": k.delta_direction,
        })
    return data


def build_dashboard(profile, kpis, charts, output_path: str = None) -> str:
    if output_path is None:
        output_path = OUTPUT_FILE

    logger.info("Building dashboard HTML...")

    viz_df = profile.viz_df
    records = _df_to_records(viz_df)

    filters = _build_filters(profile)
    chart_configs = _build_chart_configs(charts)
    kpi_configs = _build_kpi_configs(kpis)
    kpi_data = _build_kpi_template_data(kpis)

    sampled = len(profile.df) > SAMPLE_THRESHOLD

    template = Template(DASHBOARD_TEMPLATE)
    html = template.render(
        title=profile.dashboard_title,
        domain=profile.domain,
        total_rows=f"{profile.total_rows:,}",
        sampled=sampled,
        sample_size=f"{len(viz_df):,}" if sampled else "",
        default_theme=DEFAULT_THEME,
        plotly_cdn=PLOTLY_CDN,
        kpis=kpi_data,
        charts=chart_configs,
        filters=filters,
        dataset_json=json.dumps(records, default=str),
        chart_configs_json=json.dumps(chart_configs, default=str),
        kpi_configs_json=json.dumps(kpi_configs, default=str),
        filter_configs_json=json.dumps(filters, default=str),
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"Dashboard saved to: {output_path}")
    return output_path
