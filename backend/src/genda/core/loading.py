"""
CSV loading, schema detection, encoding detection, and bounded preview generation.
Pure functions without web framework dependencies.
"""

from __future__ import annotations
import io
from typing import Any
import polars as pl
import charset_normalizer

from genda.core.models import DataPreview

MAX_PREVIEW_ROWS = 50
MAX_FILE_BYTES = 100 * 1024 * 1024  # 100 MB local safety limit


class LoadError(Exception):
    """Raised when dataset loading or parsing fails safely without exposing raw row secrets."""
    pass


def detect_encoding(file_bytes: bytes) -> str:
    """Detect text encoding using charset-normalizer with fallback to utf-8."""
    if not file_bytes:
        return "utf-8"
    try:
        sample = file_bytes[:65536]
        result = charset_normalizer.from_bytes(sample).best()
        if result and result.encoding:
            return result.encoding
    except Exception:
        pass
    return "utf-8"


def load_csv_bytes(
    file_bytes: bytes,
    filename: str = "dataset.csv",
    session_id: str = "default",
    max_rows_preview: int = MAX_PREVIEW_ROWS,
) -> tuple[pl.DataFrame, DataPreview]:
    """
    Parse CSV bytes into a Polars DataFrame safely.
    Enforces size boundaries, detects encoding, and extracts schema + preview.
    """
    if len(file_bytes) > MAX_FILE_BYTES:
        raise LoadError(
            f"File exceeds maximum allowed size of {MAX_FILE_BYTES // (1024 * 1024)} MB."
        )

    if len(file_bytes.strip()) == 0:
        raise LoadError("File is empty (0 bytes).")

    encoding = detect_encoding(file_bytes)

    try:
        # Load with Polars read_csv
        # Using ignore_errors=False to detect malformed CSVs honestly
        df = pl.read_csv(
            io.BytesIO(file_bytes),
            encoding=encoding,
            infer_schema_length=10000,
            truncate_ragged_lines=False,
        )
    except Exception as e:
        # Avoid exposing raw data chunks in error message
        raise LoadError(f"Failed to parse CSV file: {type(e).__name__}: {str(e)}")

    if df.width == 0:
        raise LoadError("CSV contains no columns or failed to detect headers.")

    row_count = df.height
    col_count = df.width
    headers = df.columns

    # Map Polars dtypes to clean string representations
    column_types: dict[str, str] = {
        col: str(df.schema[col]) for col in headers
    }

    # Bounded preview: take at most max_rows_preview
    preview_df = df.head(max_rows_preview)
    preview_rows: list[dict[str, Any]] = preview_df.to_dicts()

    # Clean non-JSON serializable values like NaN or Infinity
    cleaned_preview: list[dict[str, Any]] = []
    for row in preview_rows:
        cleaned_row: dict[str, Any] = {}
        for k, v in row.items():
            if v is None:
                cleaned_row[k] = None
            elif isinstance(v, float):
                import math
                if math.isnan(v) or math.isinf(v):
                    cleaned_row[k] = None
                else:
                    cleaned_row[k] = v
            else:
                cleaned_row[k] = v
        cleaned_preview.append(cleaned_row)

    preview = DataPreview(
        session_id=session_id,
        filename=filename,
        size_bytes=len(file_bytes),
        headers=headers,
        row_count=row_count,
        col_count=col_count,
        preview_rows=cleaned_preview,
        column_types=column_types,
        encoding=encoding,
    )

    return df, preview
