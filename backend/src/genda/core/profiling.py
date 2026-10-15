"""
Dataset profiling and data quality checks using Polars primitives.
Computes deterministic, testable statistics and flags data quality warnings.
"""

from __future__ import annotations
import math
from typing import Any
import polars as pl

from genda.core.models import ColumnProfile, DatasetProfile, CategoricalFrequency


def infer_general_type(dtype: pl.DataType) -> str:
    """Classify Polars dtype into broad categories."""
    if dtype.is_numeric():
        return "numeric"
    elif dtype == pl.Boolean:
        return "boolean"
    elif dtype.is_temporal():
        return "datetime"
    elif dtype in (pl.Utf8, pl.String, pl.Categorical):
        return "categorical"
    else:
        return "unknown"


def profile_column(series: pl.Series) -> ColumnProfile:
    """Compute detailed profile metrics for a single column."""
    name = series.name
    total_count = len(series)
    null_count = series.null_count()
    null_percentage = round((null_count / total_count * 100), 2) if total_count > 0 else 0.0

    inferred_type = infer_general_type(series.dtype)
    polars_type = str(series.dtype)
    warnings: list[str] = []

    if null_percentage > 50.0:
        warnings.append(f"Severe missingness: {null_percentage}% values are null.")
    elif null_percentage > 20.0:
        warnings.append(f"High missingness: {null_percentage}% values are null.")

    # Distinct values
    try:
        distinct_count = series.n_unique()
    except Exception:
        distinct_count = 0

    is_unique = (distinct_count == total_count and total_count > 0)

    min_val: Any | None = None
    max_val: Any | None = None
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    q25: float | None = None
    q75: float | None = None
    top_frequencies: list[CategoricalFrequency] = []

    # If numeric, compute descriptive statistics
    if inferred_type == "numeric":
        valid_series = series.drop_nulls()
        if len(valid_series) > 0:
            try:
                min_raw = valid_series.min()
                max_raw = valid_series.max()
                min_val = float(min_raw) if min_raw is not None else None
                max_val = float(max_raw) if max_raw is not None else None

                mean_val = valid_series.mean()
                mean = round(float(mean_val), 4) if mean_val is not None and not math.isnan(mean_val) else None

                median_val = valid_series.median()
                median = round(float(median_val), 4) if median_val is not None and not math.isnan(median_val) else None

                std_val = valid_series.std()
                std = round(float(std_val), 4) if std_val is not None and not math.isnan(std_val) else None

                q25_val = valid_series.quantile(0.25)
                q25 = round(float(q25_val), 4) if q25_val is not None and not math.isnan(q25_val) else None

                q75_val = valid_series.quantile(0.75)
                q75 = round(float(q75_val), 4) if q75_val is not None and not math.isnan(q75_val) else None

                # Outlier detection check using IQR
                if q25 is not None and q75 is not None and std is not None:
                    iqr = q75 - q25
                    lower_bound = q25 - 1.5 * iqr
                    upper_bound = q75 + 1.5 * iqr
                    outliers_count = len(valid_series.filter((valid_series < lower_bound) | (valid_series > upper_bound)))
                    if outliers_count > 0:
                        warnings.append(f"{outliers_count} potential outlier(s) detected outside 1.5x IQR.")
            except Exception as e:
                warnings.append(f"Numeric calculation note: {type(e).__name__}")

    # For categorical / text / low cardinality, get top frequencies
    if inferred_type in ("categorical", "boolean", "unknown") or (distinct_count <= 20 and total_count > 0):
        try:
            val_counts = (
                series.value_counts(sort=True)
                .head(10)
            )
            col_names = val_counts.columns
            val_col = col_names[0]
            count_col = col_names[1]

            for row in val_counts.iter_rows(named=True):
                v = row[val_col]
                c = row[count_col]
                pct = round((c / total_count * 100), 2) if total_count > 0 else 0.0
                str_val = str(v) if v is not None else "(null)"
                top_frequencies.append(CategoricalFrequency(value=str_val, count=c, percentage=pct))
        except Exception:
            pass

    return ColumnProfile(
        name=name,
        inferred_type=inferred_type,  # type: ignore
        polars_type=polars_type,
        total_count=total_count,
        null_count=null_count,
        null_percentage=null_percentage,
        distinct_count=distinct_count,
        is_unique=is_unique,
        min_val=min_val,
        max_val=max_val,
        mean=mean,
        median=median,
        std=std,
        q25=q25,
        q75=q75,
        top_frequencies=top_frequencies,
        warnings=warnings,
    )


def profile_dataset(df: pl.DataFrame) -> DatasetProfile:
    """
    Profile an entire Polars DataFrame and identify dataset-level warnings.
    """
    row_count = df.height
    col_count = df.width
    memory_bytes = df.estimated_size()
    dataset_warnings: list[str] = []

    # Duplicate rows count
    try:
        dup_count = df.is_duplicated().sum()
    except Exception:
        dup_count = 0

    if dup_count > 0:
        pct = round(dup_count / row_count * 100, 2) if row_count > 0 else 0.0
        dataset_warnings.append(f"{dup_count} duplicate rows ({pct}%) found in dataset.")

    columns: list[ColumnProfile] = []
    for col_name in df.columns:
        col_prof = profile_column(df[col_name])
        columns.append(col_prof)

    # Dataset warnings summary
    high_null_cols = [c.name for c in columns if c.null_percentage > 40.0]
    if high_null_cols:
        dataset_warnings.append(
            f"Columns with >40% missing data: {', '.join(high_null_cols)}."
        )

    return DatasetProfile(
        row_count=row_count,
        column_count=col_count,
        columns=columns,
        duplicate_rows=dup_count,
        memory_bytes=memory_bytes,
        dataset_warnings=dataset_warnings,
    )
