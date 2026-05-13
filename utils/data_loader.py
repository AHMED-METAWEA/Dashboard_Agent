"""
Dashboard Agent — Data Loader
Loads CSV, TSV, XLSX, XLS, and JSON files with full validation.
"""

import os
import csv
import io
import json
import chardet
import pandas as pd

from config.settings import MAX_UPLOAD_MB


class DataLoadError(Exception):
    """Custom exception for all data-loading failures."""
    pass


def _detect_encoding(filepath: str) -> str:
    """Detect file encoding using chardet, with fallback chain."""
    with open(filepath, "rb") as f:
        raw = f.read(min(os.path.getsize(filepath), 1_000_000))

    detection = chardet.detect(raw)
    detected = detection.get("encoding")
    confidence = detection.get("confidence", 0)

    if detected and confidence > 0.5:
        return detected

    for fallback in ["utf-8", "latin-1", "cp1252"]:
        try:
            raw[:10000].decode(fallback)
            return fallback
        except (UnicodeDecodeError, LookupError):
            continue

    return "utf-8"


def _detect_delimiter(filepath: str, encoding: str) -> str:
    """Detect CSV/TSV delimiter using csv.Sniffer."""
    with open(filepath, "r", encoding=encoding, errors="replace") as f:
        sample = f.read(8192)

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        return dialect.delimiter
    except csv.Error:
        if filepath.lower().endswith(".tsv"):
            return "\t"
        return ","


def _load_csv(filepath: str) -> pd.DataFrame:
    """Load a CSV or TSV file with auto-detected encoding and delimiter."""
    encoding = _detect_encoding(filepath)
    delimiter = _detect_delimiter(filepath, encoding)

    try:
        df = pd.read_csv(
            filepath,
            encoding=encoding,
            delimiter=delimiter,
            low_memory=False,
            on_bad_lines="warn",
        )
    except Exception as e:
        for fallback_enc in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(
                    filepath,
                    encoding=fallback_enc,
                    delimiter=delimiter,
                    low_memory=False,
                    on_bad_lines="warn",
                )
                break
            except Exception:
                continue
        else:
            raise DataLoadError(
                f"Unable to read CSV file '{filepath}'. "
                f"Tried multiple encodings. Original error: {e}"
            )

    return df


def _load_excel(filepath: str) -> pd.DataFrame:
    """Load an Excel file (sheet 0 by default)."""
    try:
        xls = pd.ExcelFile(filepath, engine="openpyxl")
    except Exception as e:
        raise DataLoadError(
            f"Unable to open Excel file '{filepath}'. "
            f"Make sure the file is a valid .xlsx/.xls file. Error: {e}"
        )

    sheet_names = xls.sheet_names
    if len(sheet_names) > 1:
        print(
            f"⚠  Multiple sheets detected: {sheet_names}. "
            f"Reading the first sheet: '{sheet_names[0]}'."
        )

    try:
        df = pd.read_excel(xls, sheet_name=0)
    except Exception as e:
        raise DataLoadError(
            f"Unable to read sheet '{sheet_names[0]}' from '{filepath}'. Error: {e}"
        )

    return df


def _load_json(filepath: str) -> pd.DataFrame:
    """Load a JSON file — supports array-of-objects and records orientation."""
    encoding = _detect_encoding(filepath)

    try:
        with open(filepath, "r", encoding=encoding, errors="replace") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e:
        raise DataLoadError(
            f"Invalid JSON in '{filepath}'. "
            f"Make sure the file contains valid JSON. Error: {e}"
        )
    except Exception as e:
        raise DataLoadError(f"Unable to read JSON file '{filepath}'. Error: {e}")

    if isinstance(raw_data, list):
        if len(raw_data) == 0:
            raise DataLoadError(f"JSON file '{filepath}' contains an empty array.")
        if isinstance(raw_data[0], dict):
            df = pd.DataFrame(raw_data)
        else:
            raise DataLoadError(
                f"JSON file '{filepath}' contains an array but not of objects. "
                f"Expected an array of JSON objects (records)."
            )
    elif isinstance(raw_data, dict):
        try:
            df = pd.DataFrame.from_dict(raw_data, orient="columns")
        except ValueError:
            try:
                df = pd.DataFrame.from_dict(raw_data, orient="index")
            except ValueError:
                try:
                    df = pd.json_normalize(raw_data)
                except Exception:
                    raise DataLoadError(
                        f"Unable to convert JSON structure in '{filepath}' "
                        f"to a tabular DataFrame. Supported formats: "
                        f"array-of-objects or column-oriented dict."
                    )
    else:
        raise DataLoadError(
            f"JSON file '{filepath}' has an unsupported top-level type: "
            f"{type(raw_data).__name__}. Expected a JSON array or object."
        )

    return df


def _validate_dataframe(df: pd.DataFrame, filepath: str) -> None:
    """Run all post-load validation checks."""
    if df.shape[1] < 2:
        raise DataLoadError(
            f"Dataset '{filepath}' has only {df.shape[1]} column(s). "
            f"At least 2 columns are required for dashboard generation."
        )

    if df.shape[0] < 10:
        raise DataLoadError(
            f"Dataset '{filepath}' has only {df.shape[0]} row(s). "
            f"At least 10 rows are required for meaningful analysis."
        )

    if df.isnull().all().all():
        raise DataLoadError(
            f"Dataset '{filepath}' has all null values across every column. "
            f"Please provide a dataset with actual data."
        )


def _clean_string_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Strip leading/trailing whitespace from all string column values."""
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].map(
            lambda x: x.strip() if isinstance(x, str) else x
        )
    return df


def load_dataset(filepath: str) -> pd.DataFrame:
    """
    Load a dataset from a CSV, TSV, XLSX, XLS, or JSON file.

    Performs full validation:
      - File existence and size check
      - Format-specific loading with encoding/delimiter detection
      - Column count, row count, and null checks
      - Whitespace stripping on string values

    Args:
        filepath: Path to the dataset file.

    Returns:
        A clean pandas DataFrame ready for profiling.

    Raises:
        DataLoadError: On any validation or loading failure.
    """
    if not os.path.exists(filepath):
        raise DataLoadError(f"File not found: '{filepath}'")

    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    if file_size_mb > MAX_UPLOAD_MB:
        raise DataLoadError(
            f"File '{filepath}' is {file_size_mb:.1f} MB, which exceeds the "
            f"{MAX_UPLOAD_MB} MB limit. Please reduce the file size."
        )

    ext = os.path.splitext(filepath)[1].lower()

    if ext in (".csv", ".tsv"):
        df = _load_csv(filepath)
    elif ext in (".xlsx", ".xls"):
        df = _load_excel(filepath)
    elif ext == ".json":
        df = _load_json(filepath)
    else:
        raise DataLoadError(
            f"Unsupported file format: '{ext}'. "
            f"Supported formats: .csv, .tsv, .xlsx, .xls, .json"
        )

    _validate_dataframe(df, filepath)
    df = _clean_string_columns(df)

    return df
