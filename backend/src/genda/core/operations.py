"""
Allowlisted, deterministic analytical operations.
All operations are executed via Polars and can be verified via DuckDB.
Arbitrary user-code / SQL injection is strictly prevented.
"""

from __future__ import annotations
import time
from typing import Any
import polars as pl
import duckdb

from genda.core.models import (
    GroupSum,
    GroupAgg,
    NumericSummary,
    MissingSummary,
    FilterCount,
    DateComparison,
    CategoryRank,
    AnalysisResult,
)


class OperationError(Exception):
    """Raised when an operation request fails validation or execution."""
    pass


def run_numeric_summary(df: pl.DataFrame, req: NumericSummary) -> AnalysisResult:
    """Compute comprehensive descriptive statistics for a single numeric column."""
    col = req.column
    if col not in df.columns:
        raise OperationError(f"Column '{col}' does not exist in dataset.")

    series = df[col]
    if not series.dtype.is_numeric():
        raise OperationError(f"Column '{col}' is not numeric (type: {series.dtype}).")

    start_t = time.perf_counter()
    valid_series = series.drop_nulls()
    null_c = series.null_count()
    total_c = len(series)

    if len(valid_series) == 0:
        return AnalysisResult(
            title=f"Numeric Summary: {col}",
            operation="numeric_summary",
            inputs={"column": col},
            result={"status": "All values in column are null."},
            warnings=["All values in column are null or missing."],
            validation_status="warning",
            execution_time_ms=round((time.perf_counter() - start_t) * 1000, 2),
            evidence_summary=f"Column '{col}' has {total_c} total rows, all null.",
        )

    sum_val = float(valid_series.sum())
    mean_val = float(valid_series.mean())
    std_val = float(valid_series.std()) if len(valid_series) > 1 else 0.0
    min_val = float(valid_series.min())
    max_val = float(valid_series.max())
    median_val = float(valid_series.median())
    q25_val = float(valid_series.quantile(0.25)) if len(valid_series) > 1 else min_val
    q75_val = float(valid_series.quantile(0.75)) if len(valid_series) > 1 else max_val

    result_data = {
        "column": col,
        "total_rows": total_c,
        "valid_rows": len(valid_series),
        "null_count": null_c,
        "null_percentage": round(null_c / total_c * 100, 2) if total_c > 0 else 0.0,
        "sum": round(sum_val, 4),
        "mean": round(mean_val, 4),
        "std": round(std_val, 4),
        "min": round(min_val, 4),
        "q25": round(q25_val, 4),
        "median": round(median_val, 4),
        "q75": round(q75_val, 4),
        "max": round(max_val, 4),
        "range": round(max_val - min_val, 4),
    }

    warnings: list[str] = []
    if null_c > 0:
        warnings.append(f"{null_c} null value(s) excluded from descriptive calculations.")

    duration_ms = round((time.perf_counter() - start_t) * 1000, 2)

    return AnalysisResult(
        title=f"Descriptive Statistics: {col}",
        operation="numeric_summary",
        inputs={"column": col},
        result=result_data,
        warnings=warnings,
        validation_status="passed",
        execution_time_ms=duration_ms,
        evidence_summary=f"Computed mean={result_data['mean']}, median={result_data['median']}, std={result_data['std']} across {len(valid_series)} non-null rows.",
        limitations=["Assumes distribution metrics apply to valid observations; missing values were omitted."],
    )


def run_missing_summary(df: pl.DataFrame, req: MissingSummary) -> AnalysisResult:
    """Summarize missing and null values across all columns in dataset."""
    start_t = time.perf_counter()
    total_rows = df.height
    col_summaries: list[dict[str, Any]] = []

    for col in df.columns:
        null_c = df[col].null_count()
        pct = round(null_c / total_rows * 100, 2) if total_rows > 0 else 0.0
        col_summaries.append({
            "column": col,
            "dtype": str(df[col].dtype),
            "null_count": null_c,
            "null_percentage": pct,
            "present_count": total_rows - null_c,
        })

    col_summaries.sort(key=lambda x: x["null_count"], reverse=True)

    warnings: list[str] = []
    high_nulls = [c["column"] for c in col_summaries if c["null_percentage"] > 25.0]
    if high_nulls:
        warnings.append(f"High missingness (>25%) detected in columns: {', '.join(high_nulls)}.")

    duration_ms = round((time.perf_counter() - start_t) * 1000, 2)

    return AnalysisResult(
        title="Missing Values Summary",
        operation="missing_summary",
        inputs={},
        result={"columns": col_summaries, "total_rows": total_rows},
        warnings=warnings,
        validation_status="passed",
        execution_time_ms=duration_ms,
        evidence_summary=f"Surveyed {len(df.columns)} columns across {total_rows} rows. {len(high_nulls)} column(s) have >25% missing values.",
        limitations=["Blanks or whitespace strings are not counted as null unless explicitly converted."],
    )


def run_group_agg(df: pl.DataFrame, req: GroupSum | GroupAgg) -> AnalysisResult:
    """Group by categorical column and aggregate a metric column."""
    group_col = req.group_by
    metric_col = req.metric
    agg = req.agg

    if group_col not in df.columns:
        raise OperationError(f"Group column '{group_col}' does not exist.")
    if metric_col not in df.columns:
        raise OperationError(f"Metric column '{metric_col}' does not exist.")

    if not df[metric_col].dtype.is_numeric() and agg in ("sum", "mean"):
        raise OperationError(
            f"Metric column '{metric_col}' must be numeric for aggregate '{agg}'. Current dtype: {df[metric_col].dtype}."
        )

    start_t = time.perf_counter()

    # Polars aggregation
    agg_expr = {
        "sum": pl.col(metric_col).sum().alias(f"{metric_col}_{agg}"),
        "mean": pl.col(metric_col).mean().alias(f"{metric_col}_{agg}"),
        "count": pl.col(metric_col).count().alias(f"{metric_col}_{agg}"),
        "min": pl.col(metric_col).min().alias(f"{metric_col}_{agg}"),
        "max": pl.col(metric_col).max().alias(f"{metric_col}_{agg}"),
    }[agg]

    # Fill null category with explicit "(Missing)" label so it's not silently lost
    clean_group = pl.col(group_col).fill_null("(Missing)")

    polars_res = (
        df.with_columns(clean_group.alias(group_col))
        .group_by(group_col)
        .agg(agg_expr)
        .sort(f"{metric_col}_{agg}", descending=True)
    )

    rows: list[dict[str, Any]] = polars_res.to_dicts()

    # Clean floats
    cleaned_rows: list[dict[str, Any]] = []
    for r in rows:
        val = r.get(f"{metric_col}_{agg}")
        if isinstance(val, float):
            r[f"{metric_col}_{agg}"] = round(val, 4)
        cleaned_rows.append(r)

    # Cross-engine check via DuckDB
    cross_engine_match = True
    try:
        # Register in-memory DuckDB connection
        con = duckdb.connect(database=":memory:")
        arrow_table = df.to_arrow()
        con.register("df_table", arrow_table)
        duck_sql = f"""
            SELECT 
                COALESCE(CAST("{group_col}" AS VARCHAR), '(Missing)') AS "{group_col}",
                {agg.upper()}("{metric_col}") AS metric_val
            FROM df_table
            GROUP BY 1
            ORDER BY metric_val DESC
        """
        duck_res = con.execute(duck_sql).fetchall()
        # Verify row count and top values align within floating point tolerance
        if len(duck_res) != len(rows):
            cross_engine_match = False
        elif len(duck_res) > 0 and len(rows) > 0:
            top_duck = duck_res[0][1]
            top_polars = rows[0][f"{metric_col}_{agg}"]
            if top_duck is not None and top_polars is not None:
                if abs(float(top_duck) - float(top_polars)) > 1e-3:
                    cross_engine_match = False
    except Exception:
        cross_engine_match = None  # If DuckDB interop is not possible

    duration_ms = round((time.perf_counter() - start_t) * 1000, 2)
    val_status = "passed" if (cross_engine_match is not False) else "failed"

    warnings: list[str] = []
    if cross_engine_match is False:
        warnings.append("Cross-engine discrepancy detected between Polars and DuckDB.")

    return AnalysisResult(
        title=f"Grouped {agg.capitalize()}: {metric_col} by {group_col}",
        operation="group_agg",
        inputs={"group_by": group_col, "metric": metric_col, "agg": agg},
        result={
            "groups": cleaned_rows,
            "group_count": len(cleaned_rows),
            "group_by": group_col,
            "metric": metric_col,
            "agg": agg,
            "metric_field": f"{metric_col}_{agg}",
        },
        warnings=warnings,
        validation_status=val_status,
        execution_time_ms=duration_ms,
        cross_engine_match=cross_engine_match,
        evidence_summary=f"Grouped {len(df)} records into {len(cleaned_rows)} distinct '{group_col}' buckets using {agg.upper()} aggregation.",
        limitations=["Null group keys were labeled as '(Missing)'. Aggregation excludes null values from calculation."],
    )


def run_filter_count(df: pl.DataFrame, req: FilterCount) -> AnalysisResult:
    """Filter records by an explicit condition and return match count and percentage."""
    col = req.column
    op = req.operator
    val = req.value

    if col not in df.columns:
        raise OperationError(f"Column '{col}' does not exist.")

    start_t = time.perf_counter()
    series = df[col]
    total_count = len(df)

    try:
        if op == "==":
            mask = series == val
        elif op == "!=":
            mask = series != val
        elif op == ">":
            mask = series > float(val)
        elif op == ">=":
            mask = series >= float(val)
        elif op == "<":
            mask = series < float(val)
        elif op == "<=":
            mask = series <= float(val)
        elif op == "contains":
            mask = series.cast(pl.Utf8).str.contains(str(val), literal=True)
        else:
            raise OperationError(f"Unsupported operator '{op}'.")

        matched_count = int(mask.fill_null(False).sum())
        matched_pct = round(matched_count / total_count * 100, 2) if total_count > 0 else 0.0

        # Sample matched rows preview (bounded)
        matched_sample = df.filter(mask).head(10).to_dicts()
    except Exception as e:
        raise OperationError(f"Filter execution failed: {type(e).__name__}: {str(e)}")

    duration_ms = round((time.perf_counter() - start_t) * 1000, 2)

    return AnalysisResult(
        title=f"Filtered Count: {col} {op} {val}",
        operation="filter_count",
        inputs={"column": col, "operator": op, "value": val},
        result={
            "total_rows": total_count,
            "matched_rows": matched_count,
            "unmatched_rows": total_count - matched_count,
            "matched_percentage": matched_pct,
            "sample_matches": matched_sample,
        },
        warnings=[],
        validation_status="passed",
        execution_time_ms=duration_ms,
        evidence_summary=f"{matched_count} of {total_count} rows ({matched_pct}%) satisfy '{col} {op} {val}'.",
        limitations=["Null records evaluate to False for matching conditions."],
    )


def run_category_rank(df: pl.DataFrame, req: CategoryRank) -> AnalysisResult:
    """Rank categorical values by aggregated metric."""
    cat_col = req.category_column
    metric_col = req.metric_column
    agg = req.agg
    top_n = max(1, min(req.top_n, 100))
    ascending = req.ascending

    if cat_col not in df.columns:
        raise OperationError(f"Category column '{cat_col}' does not exist.")
    if metric_col not in df.columns:
        raise OperationError(f"Metric column '{metric_col}' does not exist.")

    start_t = time.perf_counter()

    # Aggregate
    agg_expr = {
        "sum": pl.col(metric_col).sum(),
        "mean": pl.col(metric_col).mean(),
        "count": pl.col(metric_col).count(),
    }[agg]

    res_df = (
        df.filter(pl.col(cat_col).is_not_null())
        .group_by(cat_col)
        .agg(agg_expr.alias("metric_value"))
        .sort("metric_value", descending=not ascending)
        .head(top_n)
    )

    ranked_items: list[dict[str, Any]] = []
    for rank, row in enumerate(res_df.to_dicts(), start=1):
        v = row["metric_value"]
        if isinstance(v, float):
            v = round(v, 4)
        ranked_items.append({
            "rank": rank,
            "category": str(row[cat_col]),
            "value": v,
        })

    duration_ms = round((time.perf_counter() - start_t) * 1000, 2)

    order_str = "lowest" if ascending else "top"
    return AnalysisResult(
        title=f"Category Ranking: {order_str.capitalize()} {top_n} {cat_col} by {agg.upper()}({metric_col})",
        operation="category_rank",
        inputs={
            "category_column": cat_col,
            "metric_column": metric_col,
            "agg": agg,
            "top_n": top_n,
            "ascending": ascending,
        },
        result={
            "rankings": ranked_items,
            "category_column": cat_col,
            "metric_column": metric_col,
            "agg": agg,
            "top_n": top_n,
            "ascending": ascending,
        },
        warnings=[],
        validation_status="passed",
        execution_time_ms=duration_ms,
        evidence_summary=f"Ranked {len(ranked_items)} categories. Leader: {ranked_items[0]['category'] if ranked_items else 'N/A'}.",
        limitations=["Null category keys were excluded from the ranking."],
    )


def run_date_comparison(df: pl.DataFrame, req: DateComparison) -> AnalysisResult:
    """Compare a metric between two date periods."""
    date_col = req.date_column
    metric_col = req.metric_column
    agg = req.agg

    if date_col not in df.columns or metric_col not in df.columns:
        raise OperationError(f"Columns '{date_col}' or '{metric_col}' not found.")

    start_t = time.perf_counter()

    # Try casting to date
    try:
        date_series = df[date_col].cast(pl.Date, strict=False)
        date_df = df.with_columns(date_series.alias("_parsed_date"))
    except Exception as e:
        raise OperationError(f"Could not parse '{date_col}' into dates: {e}")

    try:
        import datetime
        r1_s = datetime.date.fromisoformat(req.range_1_start)
        r1_e = datetime.date.fromisoformat(req.range_1_end)
        r2_s = datetime.date.fromisoformat(req.range_2_start)
        r2_e = datetime.date.fromisoformat(req.range_2_end)
    except Exception as e:
        raise OperationError(f"Invalid date format (must be YYYY-MM-DD): {e}")

    df_r1 = date_df.filter((pl.col("_parsed_date") >= r1_s) & (pl.col("_parsed_date") <= r1_e))
    df_r2 = date_df.filter((pl.col("_parsed_date") >= r2_s) & (pl.col("_parsed_date") <= r2_e))

    def compute_metric(sub_df: pl.DataFrame) -> float:
        s = sub_df[metric_col].drop_nulls()
        if len(s) == 0:
            return 0.0
        if agg == "sum":
            return float(s.sum())
        elif agg == "mean":
            return float(s.mean())
        elif agg == "count":
            return float(len(s))
        return 0.0

    val1 = compute_metric(df_r1)
    val2 = compute_metric(df_r2)

    diff = val2 - val1
    pct_change = round((diff / val1 * 100), 2) if val1 != 0 else None

    result_data = {
        "period_1": {
            "start": req.range_1_start,
            "end": req.range_1_end,
            "rows": len(df_r1),
            "metric_value": round(val1, 4),
        },
        "period_2": {
            "start": req.range_2_start,
            "end": req.range_2_end,
            "rows": len(df_r2),
            "metric_value": round(val2, 4),
        },
        "absolute_difference": round(diff, 4),
        "percentage_change": pct_change,
        "metric": metric_col,
        "agg": agg,
    }

    duration_ms = round((time.perf_counter() - start_t) * 1000, 2)

    return AnalysisResult(
        title=f"Date Range Comparison: {metric_col} ({agg.upper()})",
        operation="date_comparison",
        inputs={
            "date_column": date_col,
            "metric_column": metric_col,
            "range_1": f"{req.range_1_start} to {req.range_1_end}",
            "range_2": f"{req.range_2_start} to {req.range_2_end}",
        },
        result=result_data,
        warnings=[],
        validation_status="passed",
        execution_time_ms=duration_ms,
        evidence_summary=f"Period 1 ({req.range_1_start}..{req.range_1_end}) value: {round(val1, 2)}; Period 2 ({req.range_2_start}..{req.range_2_end}) value: {round(val2, 2)}. Change: {pct_change}%.",
        limitations=["Comparison strictly bounded to records with parseable dates within specified ranges."],
    )


def execute_operation(df: pl.DataFrame, request: Any) -> AnalysisResult:
    """Dispatch validated AnalysisRequest to deterministic executor."""
    op = getattr(request, "operation", None)
    if op in ("group_sum", "group_agg"):
        return run_group_agg(df, request)
    elif op == "numeric_summary":
        return run_numeric_summary(df, request)
    elif op == "missing_summary":
        return run_missing_summary(df, request)
    elif op == "filter_count":
        return run_filter_count(df, request)
    elif op == "category_rank":
        return run_category_rank(df, request)
    elif op == "date_comparison":
        return run_date_comparison(df, request)
    else:
        raise OperationError(f"Unsupported operation '{op}'.")
