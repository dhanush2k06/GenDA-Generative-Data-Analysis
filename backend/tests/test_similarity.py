"""
Similarity matching and recipe adaptation tests.
Verifies schema fingerprint determinism, 3-stage scoring, explanations,
and column role binding.
"""

import pytest
import secrets
from genda.similarity.fingerprint import compute_schema_fingerprint, extract_column_features
from genda.similarity.matcher import compare_datasets
from genda.similarity.adapter import adapt_recipe_to_dataset, AdaptationError


def test_schema_fingerprint_determinism():
    cols_1 = [
        {"name": "Age", "type_class": "numeric"},
        {"name": "Income", "type_class": "numeric"},
        {"name": "City", "type_class": "categorical"},
    ]
    # Permuted order and case differences
    cols_2 = [
        {"name": "city", "type_class": "categorical"},
        {"name": "age", "type_class": "numeric"},
        {"name": "income", "type_class": "numeric"},
    ]

    fp_1 = compute_schema_fingerprint(cols_1)
    fp_2 = compute_schema_fingerprint(cols_2)

    assert fp_1 == fp_2
    assert len(fp_1) == 32


def test_similarity_matching_exact_and_structural():
    source_cols = [
        {"name": "user_id", "type_class": "numeric", "null_rate_bucket": "none", "distinct_ratio_bucket": "high"},
        {"name": "signup_date", "type_class": "temporal", "null_rate_bucket": "none", "distinct_ratio_bucket": "moderate"},
        {"name": "plan_type", "type_class": "categorical", "null_rate_bucket": "none", "distinct_ratio_bucket": "low"},
        {"name": "mrr", "type_class": "numeric", "null_rate_bucket": "none", "distinct_ratio_bucket": "high"},
    ]
    source_fp = compute_schema_fingerprint(source_cols)

    # 1. Exact match target
    target_exact = {
        "id": secrets.token_hex(16),
        "name": "Historical Subscriptions",
        "fingerprint": source_fp.hex(),
        "columns": source_cols,
        "row_count": 500,
    }
    match_exact = compare_datasets(source_fp, source_cols, 500, target_exact)
    assert match_exact.composite_score == 1.0
    assert match_exact.stage == "exact_schema_match"
    assert "Exact schema match" in match_exact.explanation

    # 2. Structural match (slightly different column names and 1 extra column)
    target_similar_cols = [
        {"name": "user_id", "type_class": "numeric", "null_rate_bucket": "none", "distinct_ratio_bucket": "high"},
        {"name": "plan", "type_class": "categorical", "null_rate_bucket": "none", "distinct_ratio_bucket": "low"},
        {"name": "mrr_revenue", "type_class": "numeric", "null_rate_bucket": "none", "distinct_ratio_bucket": "high"},
        {"name": "discount_code", "type_class": "categorical", "null_rate_bucket": "low", "distinct_ratio_bucket": "low"},
    ]
    target_similar_fp = compute_schema_fingerprint(target_similar_cols)
    target_similar = {
        "id": secrets.token_hex(16),
        "name": "Q2 Billing",
        "fingerprint": target_similar_fp.hex(),
        "columns": target_similar_cols,
        "row_count": 400,
    }

    match_similar = compare_datasets(source_fp, source_cols, 500, target_similar)
    assert match_similar.composite_score >= 0.50
    assert "Matched" in match_similar.explanation

    # 3. Completely dissimilar target
    dissimilar_cols = [
        {"name": "temperature_c", "type_class": "numeric", "null_rate_bucket": "none", "distinct_ratio_bucket": "high"},
        {"name": "humidity_pct", "type_class": "numeric", "null_rate_bucket": "none", "distinct_ratio_bucket": "high"},
        {"name": "sensor_location", "type_class": "categorical", "null_rate_bucket": "none", "distinct_ratio_bucket": "low"},
    ]
    dissimilar_fp = compute_schema_fingerprint(dissimilar_cols)
    target_dissimilar = {
        "id": secrets.token_hex(16),
        "name": "Weather Sensor Readings",
        "fingerprint": dissimilar_fp.hex(),
        "columns": dissimilar_cols,
        "row_count": 1000,
    }

    match_dissimilar = compare_datasets(source_fp, source_cols, 500, target_dissimilar)
    assert match_dissimilar.composite_score < 0.40


def test_recipe_adaptation_and_validation():
    recipe_spec = {
        "operation": "group_sum",
        "roles": {
            "group_by": {"type_class": "categorical"},
            "metric": {"type_class": "numeric"},
            "agg": "mean",
        },
    }

    dataset_cols = [
        {"name": "department", "type_class": "categorical"},
        {"name": "salary", "type_class": "numeric"},
        {"name": "hire_date", "type_class": "temporal"},
    ]

    # Valid mapping
    valid_mapping = {"group_by": "department", "metric": "salary"}
    adapted = adapt_recipe_to_dataset(recipe_spec, dataset_cols, valid_mapping)
    assert adapted["is_valid"] is True
    assert adapted["operation"] == "group_sum"
    assert adapted["parameters"]["group_by"] == "department"
    assert adapted["parameters"]["metric"] == "salary"
    assert adapted["parameters"]["agg"] == "mean"

    # Missing mapping
    with pytest.raises(AdaptationError, match="Missing column mapping"):
        adapt_recipe_to_dataset(recipe_spec, dataset_cols, {"group_by": "department"})

    # Nonexistent column
    with pytest.raises(AdaptationError, match="does not exist in target dataset"):
        adapt_recipe_to_dataset(recipe_spec, dataset_cols, {"group_by": "department", "metric": "nonexistent"})
