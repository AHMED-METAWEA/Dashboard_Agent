"""
Dashboard Agent — KPI Extractor
Rule-based KPI detection — no Groq call needed.
Selects 4-6 KPI metrics based on column name keywords, variance ranking,
and optional period-over-period delta computation.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd

from config.settings import (
    COUNT_KEYWORDS, MAX_KPIS, MEAN_KEYWORDS, MIN_KPIS, SUM_KEYWORDS,
)
from utils.formatters import format_number

logger = logging.getLogger(__name__)


@dataclass
class KPISpec:
    label: str
    raw_value: float
    formatted_value: str
    aggregation: str
    source_column: str
    delta_pct: Optional[float] = None
    delta_direction: Optional[str] = None
    is_recomputable: bool = True
    js_aggregation: str = "sum"


def _score_column(col_name: str, series: pd.Series) -> dict:
    col_lower = col_name.lower().replace("_", " ").replace("-", " ")
    score = 0
    aggregation = "sum"
    js_aggregation = "sum"

    for kw in SUM_KEYWORDS:
        if kw in col_lower:
            score += 10
            aggregation = "sum"
            js_aggregation = "sum"
            break

    for kw in MEAN_KEYWORDS:
        if kw in col_lower:
            score += 8
            aggregation = "mean"
            js_aggregation = "mean"
            break

    for kw in COUNT_KEYWORDS:
        if kw in col_lower:
            score += 6
            aggregation = "count"
            js_aggregation = "count"
            break

    non_null = series.dropna()
    if len(non_null) > 1:
        try:
            cv = non_null.std() / abs(non_null.mean()) if non_null.mean() != 0 else 0
            score += min(cv * 2, 5)
        except (ZeroDivisionError, ValueError):
            pass

    if score == 0:
        value_range = non_null.max() - non_null.min() if len(non_null) > 0 else 0
        if value_range > 1000:
            aggregation = "sum"
            js_aggregation = "sum"
        else:
            aggregation = "mean"
            js_aggregation = "mean"
        score = 1

    return {"score": score, "aggregation": aggregation, "js_aggregation": js_aggregation}


def _compute_delta(df, datetime_col, value_col, aggregation):
    try:
        dt_series = df[datetime_col]
        if not pd.api.types.is_datetime64_any_dtype(dt_series):
            dt_series = pd.to_datetime(dt_series, format="mixed", dayfirst=False)

        sorted_df = df.sort_values(datetime_col)
        n_rows = len(sorted_df)

        unique_periods = dt_series.dt.to_period("M").nunique()
        if unique_periods < 2:
            unique_periods = dt_series.dt.to_period("W").nunique()
        if unique_periods < 2:
            return None, None

        period_size = max(1, n_rows // unique_periods)
        recent = sorted_df.tail(period_size)
        previous = sorted_df.iloc[max(0, n_rows - 2 * period_size):n_rows - period_size]

        if len(previous) == 0:
            return None, None

        if aggregation == "sum":
            recent_val = recent[value_col].sum()
            prev_val = previous[value_col].sum()
        elif aggregation == "mean":
            recent_val = recent[value_col].mean()
            prev_val = previous[value_col].mean()
        else:
            recent_val = len(recent)
            prev_val = len(previous)

        if prev_val == 0:
            return None, None

        delta_pct = ((recent_val - prev_val) / abs(prev_val)) * 100
        direction = "up" if delta_pct >= 0 else "down"
        return round(delta_pct, 1), direction
    except Exception as e:
        logger.warning(f"Delta computation failed for '{value_col}': {e}")
        return None, None


def _make_label(col_name, aggregation):
    label = col_name.replace("_", " ").replace("-", " ").strip()
    words = label.split()
    label = " ".join(w.capitalize() for w in words)
    prefix_map = {"sum": "Total", "mean": "Avg", "count": "Total"}
    prefix = prefix_map.get(aggregation, "")
    if prefix.lower() in label.lower():
        return label
    return f"{prefix} {label}" if prefix else label


def extract_kpis(profile) -> List[KPISpec]:
    df = profile.df
    kpis = []

    scored_columns = []
    for col in profile.numeric_cols:
        result = _score_column(col, df[col])
        scored_columns.append({"column": col, **result})
    scored_columns.sort(key=lambda x: x["score"], reverse=True)

    max_numeric_kpis = MAX_KPIS - 1
    selected = scored_columns[:max_numeric_kpis]

    primary_datetime = profile.datetime_cols[0] if profile.datetime_cols else None
    delta_computed_for = None

    for item in selected:
        col = item["column"]
        agg = item["aggregation"]
        js_agg = item["js_aggregation"]
        non_null = df[col].dropna()
        if len(non_null) == 0:
            continue

        if agg == "sum":
            raw_value = float(non_null.sum())
        elif agg == "mean":
            raw_value = float(non_null.mean())
        else:
            raw_value = float(len(non_null))

        formatted = format_number(raw_value, column_name=col, aggregation=agg)
        label = _make_label(col, agg)

        delta_pct = None
        delta_direction = None
        if primary_datetime and delta_computed_for is None:
            delta_pct, delta_direction = _compute_delta(df, primary_datetime, col, agg)
            if delta_pct is not None:
                delta_computed_for = col

        kpis.append(KPISpec(
            label=label, raw_value=raw_value, formatted_value=formatted,
            aggregation=agg, source_column=col, delta_pct=delta_pct,
            delta_direction=delta_direction, is_recomputable=True, js_aggregation=js_agg,
        ))

    kpis.append(KPISpec(
        label="Total Records", raw_value=float(profile.total_rows),
        formatted_value=f"{profile.total_rows:,}", aggregation="count",
        source_column="__total_rows__", is_recomputable=True, js_aggregation="count",
    ))

    if len(kpis) < MIN_KPIS and profile.numeric_cols:
        remaining = [s for s in scored_columns if s["column"] not in [k.source_column for k in kpis]]
        for item in remaining:
            if len(kpis) >= MIN_KPIS:
                break
            col = item["column"]
            agg = item["aggregation"]
            non_null = df[col].dropna()
            if len(non_null) == 0:
                continue
            raw_value = float(non_null.sum()) if agg == "sum" else float(non_null.mean())
            formatted = format_number(raw_value, column_name=col, aggregation=agg)
            label = _make_label(col, agg)
            kpis.insert(-1, KPISpec(
                label=label, raw_value=raw_value, formatted_value=formatted,
                aggregation=agg, source_column=col, is_recomputable=True,
                js_aggregation=item["js_aggregation"],
            ))

    logger.info(f"Extracted {len(kpis)} KPIs: {[k.label for k in kpis]}")
    return kpis
