"""
Dashboard Agent — Data Profiler
Column type detection, per-column statistics, large-dataset sampling,
and domain detection via Groq LLM.
"""

import time
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from config.settings import (
    CATEGORICAL_MAX_UNIQUE,
    CATEGORICAL_MAX_RATIO,
    GROQ_MAX_TOKENS,
    GROQ_MODEL,
    GROQ_RETRY_WAIT_SEC,
    GROQ_TEMPERATURE,
    NUMERIC_MIN_NON_NULL_RATIO,
    SAMPLE_SIZE,
    SAMPLE_THRESHOLD,
)
from utils.json_parser import extract_json

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class ColumnProfile:
    """Statistics and metadata for a single column."""
    name: str
    dtype: str
    col_type: str  # numeric, categorical, datetime, boolean, high_cardinality
    stats: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataProfile:
    """Complete profile of a dataset including domain detection results."""
    df: pd.DataFrame
    viz_df: pd.DataFrame
    total_rows: int
    total_cols: int
    columns: Dict[str, ColumnProfile] = field(default_factory=dict)
    numeric_cols: List[str] = field(default_factory=list)
    categorical_cols: List[str] = field(default_factory=list)
    datetime_cols: List[str] = field(default_factory=list)
    boolean_cols: List[str] = field(default_factory=list)
    high_cardinality_cols: List[str] = field(default_factory=list)
    domain: str = "General"
    domain_confidence: int = 50
    dashboard_title: str = "Executive Dashboard"
    domain_context: str = ""
    overall_null_pct: float = 0.0


# ═══════════════════════════════════════════════════════════════════════
# Column Type Classification
# ═══════════════════════════════════════════════════════════════════════

def _classify_columns(df: pd.DataFrame) -> Dict[str, str]:
    """
    Classify every column into exactly one type:
      numeric, categorical, datetime, boolean, high_cardinality
    """
    classifications = {}

    for col in df.columns:
        series = df[col]
        dtype = str(series.dtype)
        non_null = series.dropna()
        n_unique = non_null.nunique()
        n_total = len(series)
        unique_ratio = n_unique / n_total if n_total > 0 else 0

        # ── Boolean check (exactly 2 unique non-null values) ─────────
        if n_unique == 2:
            classifications[col] = "boolean"
            continue

        # ── Numeric check ────────────────────────────────────────────
        if pd.api.types.is_numeric_dtype(series):
            non_null_ratio = len(non_null) / n_total if n_total > 0 else 0
            if non_null_ratio >= NUMERIC_MIN_NON_NULL_RATIO:
                classifications[col] = "numeric"
            else:
                classifications[col] = "numeric"
            continue

        # ── Datetime check ───────────────────────────────────────────
        if pd.api.types.is_datetime64_any_dtype(series):
            classifications[col] = "datetime"
            continue

        if dtype == "object":
            sample_vals = non_null.head(50).astype(str)
            try:
                parsed = pd.to_datetime(sample_vals, format="mixed", dayfirst=False)
                success_rate = parsed.notna().sum() / len(sample_vals) if len(sample_vals) > 0 else 0
                if success_rate > 0.8:
                    classifications[col] = "datetime"
                    continue
            except (ValueError, TypeError, OverflowError):
                pass

        # ── Categorical vs High Cardinality ──────────────────────────
        if dtype == "object" or str(dtype) == "string":
            if n_unique < CATEGORICAL_MAX_UNIQUE or unique_ratio < CATEGORICAL_MAX_RATIO:
                classifications[col] = "categorical"
            else:
                classifications[col] = "high_cardinality"
            continue

        # ── Fallback: treat as categorical if few unique, else high_cardinality
        if n_unique < CATEGORICAL_MAX_UNIQUE:
            classifications[col] = "categorical"
        else:
            classifications[col] = "high_cardinality"

    return classifications


# ═══════════════════════════════════════════════════════════════════════
# Per-Column Statistics
# ═══════════════════════════════════════════════════════════════════════

def _compute_numeric_stats(series: pd.Series) -> Dict[str, Any]:
    """Compute statistics for a numeric column."""
    non_null = series.dropna()
    total = len(series)

    stats = {
        "min": float(non_null.min()) if len(non_null) > 0 else 0,
        "max": float(non_null.max()) if len(non_null) > 0 else 0,
        "mean": float(non_null.mean()) if len(non_null) > 0 else 0,
        "median": float(non_null.median()) if len(non_null) > 0 else 0,
        "std": float(non_null.std()) if len(non_null) > 1 else 0,
        "null_pct": round((series.isna().sum() / total) * 100, 2) if total > 0 else 0,
        "skewness": float(non_null.skew()) if len(non_null) > 2 else 0,
    }

    if len(non_null) > 0:
        value_counts = non_null.value_counts()
        stats["top_value"] = float(value_counts.index[0])
    else:
        stats["top_value"] = 0

    return stats


def _compute_categorical_stats(series: pd.Series) -> Dict[str, Any]:
    """Compute statistics for a categorical column."""
    non_null = series.dropna()
    total = len(series)
    vc = non_null.value_counts().head(10)

    top_10 = []
    for val, cnt in vc.items():
        top_10.append({
            "value": str(val),
            "count": int(cnt),
            "pct": round((cnt / len(non_null)) * 100, 2) if len(non_null) > 0 else 0,
        })

    return {
        "unique_count": int(non_null.nunique()),
        "null_pct": round((series.isna().sum() / total) * 100, 2) if total > 0 else 0,
        "top_10": top_10,
    }


def _compute_datetime_stats(series: pd.Series) -> Dict[str, Any]:
    """Compute statistics for a datetime column."""
    total = len(series)

    if not pd.api.types.is_datetime64_any_dtype(series):
        try:
            series = pd.to_datetime(series, format="mixed", dayfirst=False)
        except (ValueError, TypeError):
            return {
                "min_date": None,
                "max_date": None,
                "range_days": 0,
                "null_pct": round((series.isna().sum() / total) * 100, 2) if total > 0 else 0,
                "has_time_component": False,
            }

    non_null = series.dropna()

    has_time = False
    if len(non_null) > 0:
        sample = non_null.head(20)
        has_time = any(
            t.hour != 0 or t.minute != 0 or t.second != 0
            for t in sample
            if hasattr(t, "hour")
        )

    min_date = non_null.min() if len(non_null) > 0 else None
    max_date = non_null.max() if len(non_null) > 0 else None
    range_days = (max_date - min_date).days if min_date and max_date else 0

    return {
        "min_date": str(min_date) if min_date else None,
        "max_date": str(max_date) if max_date else None,
        "range_days": int(range_days),
        "null_pct": round((series.isna().sum() / total) * 100, 2) if total > 0 else 0,
        "has_time_component": has_time,
    }


def _compute_boolean_stats(series: pd.Series) -> Dict[str, Any]:
    """Compute statistics for a boolean column."""
    total = len(series)
    non_null = series.dropna()
    vc = non_null.value_counts()

    values = list(vc.index)
    counts = list(vc.values)

    return {
        "true_count": int(counts[0]) if len(counts) > 0 else 0,
        "false_count": int(counts[1]) if len(counts) > 1 else 0,
        "true_label": str(values[0]) if len(values) > 0 else "True",
        "false_label": str(values[1]) if len(values) > 1 else "False",
        "null_pct": round((series.isna().sum() / total) * 100, 2) if total > 0 else 0,
    }


def _compute_high_cardinality_stats(series: pd.Series) -> Dict[str, Any]:
    """Compute statistics for a high-cardinality column."""
    total = len(series)
    non_null = series.dropna()

    return {
        "unique_count": int(non_null.nunique()),
        "null_pct": round((series.isna().sum() / total) * 100, 2) if total > 0 else 0,
        "sample_values": [str(v) for v in non_null.head(5).tolist()],
    }


# ═══════════════════════════════════════════════════════════════════════
# Large Dataset Sampling
# ═══════════════════════════════════════════════════════════════════════

def _create_viz_sample(df: pd.DataFrame, categorical_cols: List[str]) -> pd.DataFrame:
    """
    Create a stratified random sample for visualization if the dataset
    exceeds SAMPLE_THRESHOLD rows.
    """
    if len(df) <= SAMPLE_THRESHOLD:
        return df.copy()

    logger.info(
        f"Dataset has {len(df):,} rows (> {SAMPLE_THRESHOLD:,}). "
        f"Creating visualization sample of {SAMPLE_SIZE:,} rows."
    )

    if categorical_cols:
        strat_col = categorical_cols[0]
        try:
            vc = df[strat_col].value_counts()
            min_group = vc.min()
            if min_group >= 2:
                from sklearn.model_selection import StratifiedShuffleSplit
                sss = StratifiedShuffleSplit(n_splits=1, train_size=SAMPLE_SIZE, random_state=42)
                idx, _ = next(sss.split(df, df[strat_col]))
                return df.iloc[idx].copy()
        except Exception:
            pass

    return df.sample(n=min(SAMPLE_SIZE, len(df)), random_state=42).copy()


# ═══════════════════════════════════════════════════════════════════════
# Domain Detection via Groq
# ═══════════════════════════════════════════════════════════════════════

def _detect_domain(df: pd.DataFrame, groq_client) -> Dict[str, Any]:
    """
    Use Groq LLM to detect the business domain of the dataset.
    Returns domain, confidence, dashboard_title, and domain_context.
    """
    col_info = []
    for col in df.columns:
        dtype_str = str(df[col].dtype)
        col_info.append({"column": col, "dtype": dtype_str})

    sample_rows = df.head(5).fillna("").to_dict(orient="records")
    for row in sample_rows:
        for k, v in row.items():
            if hasattr(v, "isoformat"):
                row[k] = v.isoformat()
            elif isinstance(v, (np.integer,)):
                row[k] = int(v)
            elif isinstance(v, (np.floating,)):
                row[k] = float(v)

    prompt = (
        "You are a data analyst. Given these column names and sample data, identify "
        "the business domain and return ONLY this JSON — no markdown, no explanation:\n"
        '{"domain": "", "confidence": <0-100>, '
        '"dashboard_title": "", '
        '"domain_context": ""}\n\n'
        f"Columns:\n{json.dumps(col_info, indent=2)}\n\n"
        f"Sample rows (first 5):\n{json.dumps(sample_rows, indent=2, default=str)}"
    )

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=GROQ_TEMPERATURE,
            max_tokens=GROQ_MAX_TOKENS,
        )
        raw = response.choices[0].message.content
        result = extract_json(raw)

        return {
            "domain": result.get("domain", "General"),
            "domain_confidence": int(result.get("confidence", 50)),
            "dashboard_title": result.get("dashboard_title", "Executive Dashboard"),
            "domain_context": result.get("domain_context", ""),
        }

    except Exception as e:
        logger.warning(f"Domain detection failed: {e}. Using defaults.")
        return {
            "domain": "General",
            "domain_confidence": 50,
            "dashboard_title": "Executive Dashboard",
            "domain_context": "",
        }


# ═══════════════════════════════════════════════════════════════════════
# Main Profiling Function
# ═══════════════════════════════════════════════════════════════════════

def profile_dataset(df: pd.DataFrame, groq_client) -> DataProfile:
    """
    Profile a dataset: classify columns, compute statistics, create
    visualization sample, and detect domain via Groq.

    Args:
        df: Clean pandas DataFrame from data_loader.
        groq_client: Initialized Groq client instance.

    Returns:
        A fully populated DataProfile dataclass.
    """
    logger.info(f"Profiling dataset: {len(df):,} rows × {len(df.columns)} columns")

    # ── Step 1: Classify columns ─────────────────────────────────────
    classifications = _classify_columns(df)

    numeric_cols = [c for c, t in classifications.items() if t == "numeric"]
    categorical_cols = [c for c, t in classifications.items() if t == "categorical"]
    datetime_cols = [c for c, t in classifications.items() if t == "datetime"]
    boolean_cols = [c for c, t in classifications.items() if t == "boolean"]
    high_cardinality_cols = [c for c, t in classifications.items() if t == "high_cardinality"]

    # ── Step 2: Convert datetime columns ─────────────────────────────
    for col in datetime_cols:
        if not pd.api.types.is_datetime64_any_dtype(df[col]):
            try:
                df[col] = pd.to_datetime(df[col], format="mixed", dayfirst=False)
            except (ValueError, TypeError):
                logger.warning(f"Could not parse column '{col}' as datetime.")

    # ── Step 3: Compute per-column statistics (on FULL df) ───────────
    columns = {}
    stat_funcs = {
        "numeric": _compute_numeric_stats,
        "categorical": _compute_categorical_stats,
        "datetime": _compute_datetime_stats,
        "boolean": _compute_boolean_stats,
        "high_cardinality": _compute_high_cardinality_stats,
    }

    for col in df.columns:
        col_type = classifications.get(col, "high_cardinality")
        compute_fn = stat_funcs.get(col_type, _compute_high_cardinality_stats)
        stats = compute_fn(df[col])

        columns[col] = ColumnProfile(
            name=col,
            dtype=str(df[col].dtype),
            col_type=col_type,
            stats=stats,
        )

    # ── Step 4: Create visualization sample ──────────────────────────
    viz_df = _create_viz_sample(df, categorical_cols)

    # ── Step 5: Detect domain via Groq ───────────────────────────────
    domain_info = _detect_domain(df, groq_client)

    # ── Step 6: Compute overall null percentage ──────────────────────
    total_cells = df.shape[0] * df.shape[1]
    total_nulls = df.isna().sum().sum()
    overall_null_pct = round((total_nulls / total_cells) * 100, 2) if total_cells > 0 else 0

    profile = DataProfile(
        df=df,
        viz_df=viz_df,
        total_rows=len(df),
        total_cols=len(df.columns),
        columns=columns,
        numeric_cols=numeric_cols,
        categorical_cols=categorical_cols,
        datetime_cols=datetime_cols,
        boolean_cols=boolean_cols,
        high_cardinality_cols=high_cardinality_cols,
        domain=domain_info["domain"],
        domain_confidence=domain_info["domain_confidence"],
        dashboard_title=domain_info["dashboard_title"],
        domain_context=domain_info["domain_context"],
        overall_null_pct=overall_null_pct,
    )

    logger.info(
        f"Profile complete — Domain: {profile.domain} "
        f"({profile.domain_confidence}% confidence) | "
        f"Numeric: {len(numeric_cols)}, Categorical: {len(categorical_cols)}, "
        f"Datetime: {len(datetime_cols)}, Boolean: {len(boolean_cols)}"
    )

    return profile
