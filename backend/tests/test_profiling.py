"""
Known-answer unit tests for data profiling.
"""

import io
import polars as pl
from genda.core.profiling import profile_dataset, profile_column
from tests.fixtures.synthetic_data import SYNTHETIC_CSV_BYTES, KNOWN_ANSWERS


def test_profiling_known_answers():
    df = pl.read_csv(io.BytesIO(SYNTHETIC_CSV_BYTES))
    profile = profile_dataset(df)

    assert profile.row_count == KNOWN_ANSWERS["total_rows"]
    assert profile.column_count == KNOWN_ANSWERS["total_cols"]

    # Check amount column profile
    amount_prof = next(c for c in profile.columns if c.name == "amount")
    assert amount_prof.inferred_type == "numeric"
    assert amount_prof.null_count == KNOWN_ANSWERS["amount_null_count"]
    assert amount_prof.min_val == KNOWN_ANSWERS["amount_min"]
    assert amount_prof.max_val == KNOWN_ANSWERS["amount_max"]
    assert amount_prof.mean == KNOWN_ANSWERS["amount_mean"]

    # Check category column profile
    cat_prof = next(c for c in profile.columns if c.name == "category")
    assert cat_prof.inferred_type == "categorical"
    assert cat_prof.null_count == 0
    assert cat_prof.distinct_count == 2
