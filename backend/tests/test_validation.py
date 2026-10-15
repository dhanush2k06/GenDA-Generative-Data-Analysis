"""
Tests for cross-engine verification between Polars and DuckDB.
"""

import io
import polars as pl
from genda.core.validation import verify_sum_cross_engine
from tests.fixtures.synthetic_data import SYNTHETIC_CSV_BYTES


def test_cross_engine_verification():
    df = pl.read_csv(io.BytesIO(SYNTHETIC_CSV_BYTES))
    polars_result = [
        {"category": "A", "amount_sum": 60.0},
        {"category": "B", "amount_sum": 40.0},
    ]

    is_match, reason = verify_sum_cross_engine(
        df=df,
        group_col="category",
        metric_col="amount",
        polars_result=polars_result,
    )
    assert is_match is True
    assert "exact precision" in reason
