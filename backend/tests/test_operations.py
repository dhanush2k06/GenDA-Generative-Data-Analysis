"""
Known-answer unit tests for deterministic operations.
"""

import io
import polars as pl
from genda.core.operations import (
    run_group_agg,
    run_numeric_summary,
    run_missing_summary,
    run_filter_count,
    run_category_rank,
    run_date_comparison,
)
from genda.core.models import (
    GroupSum,
    NumericSummary,
    MissingSummary,
    FilterCount,
    CategoryRank,
    DateComparison,
)
from tests.fixtures.synthetic_data import SYNTHETIC_CSV_BYTES, KNOWN_ANSWERS


def test_group_sum_known_answers():
    df = pl.read_csv(io.BytesIO(SYNTHETIC_CSV_BYTES))
    req = GroupSum(group_by="category", metric="amount")
    res = run_group_agg(df, req)

    assert res.validation_status == "passed"
    assert res.cross_engine_match is True

    groups = {g["category"]: g["amount_sum"] for g in res.result["groups"]}
    assert groups["A"] == KNOWN_ANSWERS["group_sum_A"]
    assert groups["B"] == KNOWN_ANSWERS["group_sum_B"]


def test_numeric_summary_known_answers():
    df = pl.read_csv(io.BytesIO(SYNTHETIC_CSV_BYTES))
    req = NumericSummary(column="amount")
    res = run_numeric_summary(df, req)

    assert res.validation_status == "passed"
    data = res.result
    assert data["sum"] == KNOWN_ANSWERS["amount_sum"]
    assert data["mean"] == KNOWN_ANSWERS["amount_mean"]
    assert data["min"] == KNOWN_ANSWERS["amount_min"]
    assert data["max"] == KNOWN_ANSWERS["amount_max"]
    assert data["null_count"] == KNOWN_ANSWERS["amount_null_count"]


def test_missing_summary():
    df = pl.read_csv(io.BytesIO(SYNTHETIC_CSV_BYTES))
    req = MissingSummary()
    res = run_missing_summary(df, req)

    assert res.validation_status == "passed"
    amount_stat = next(c for c in res.result["columns"] if c["column"] == "amount")
    assert amount_stat["null_count"] == 1


def test_filter_count():
    df = pl.read_csv(io.BytesIO(SYNTHETIC_CSV_BYTES))
    req = FilterCount(column="amount", operator=">", value=25)
    res = run_filter_count(df, req)

    assert res.validation_status == "passed"
    assert res.result["matched_rows"] == 2  # 30 and 40


def test_category_rank():
    df = pl.read_csv(io.BytesIO(SYNTHETIC_CSV_BYTES))
    req = CategoryRank(category_column="category", metric_column="amount", agg="sum", top_n=5)
    res = run_category_rank(df, req)

    assert res.validation_status == "passed"
    rankings = res.result["rankings"]
    assert rankings[0]["category"] == "A"
    assert rankings[0]["value"] == 60.0
