"""
Dataset schema fingerprinting and structural feature extraction.
Computes a deterministic hash of normalized schema signatures.
"""

from __future__ import annotations
import hashlib
import json
from typing import List, Dict, Any


def bucket_null_rate(null_rate: float) -> str:
    if null_rate <= 0.001:
        return "none"
    if null_rate <= 0.05:
        return "low"
    if null_rate <= 0.20:
        return "moderate"
    return "high"


def bucket_distinct_ratio(distinct_ratio: float) -> str:
    if distinct_ratio <= 0.01:
        return "low_cardinality"
    if distinct_ratio <= 0.20:
        return "moderate_cardinality"
    if distinct_ratio <= 0.80:
        return "high_cardinality"
    return "unique"


def bucket_skewness(skewness: float | None) -> str:
    if skewness is None:
        return "normal"
    val = abs(skewness)
    if val < 0.5:
        return "symmetric"
    if val < 1.0:
        return "moderate_skew"
    return "high_skew"


def extract_column_features(col_info: Dict[str, Any], total_rows: int) -> Dict[str, Any]:
    """
    Extracts structural metadata features for similarity matching.
    Never includes raw sample values.
    """
    name = str(col_info.get("name", "")).strip().lower()
    type_class = str(col_info.get("type", "string")).lower()

    # Map engine types to broad classes
    if any(t in type_class for t in ("int", "float", "numeric", "double", "decimal")):
        broad_type = "numeric"
    elif any(t in type_class for t in ("date", "time", "timestamp")):
        broad_type = "temporal"
    elif any(t in type_class for t in ("bool", "boolean")):
        broad_type = "boolean"
    else:
        broad_type = "categorical"

    null_count = int(col_info.get("null_count", 0))
    distinct_count = int(col_info.get("distinct_count", 0))
    null_rate = (null_count / total_rows) if total_rows > 0 else 0.0
    distinct_ratio = (distinct_count / total_rows) if total_rows > 0 else 0.0

    return {
        "name": name,
        "type_class": broad_type,
        "null_rate_bucket": bucket_null_rate(null_rate),
        "distinct_ratio_bucket": bucket_distinct_ratio(distinct_ratio),
        "skew_bucket": bucket_skewness(col_info.get("skewness")),
    }


def compute_schema_fingerprint(columns_metadata: List[Dict[str, Any]]) -> bytes:
    """
    Generates a 32-byte deterministic SHA-256 fingerprint for a dataset schema.
    Sorts columns by normalized name and encodes names and broad types.
    """
    normalized = []
    for col in columns_metadata:
        name = str(col.get("name", "")).strip().lower()
        t = str(col.get("type_class", col.get("type", "string"))).lower()
        normalized.append(f"{name}:{t}")

    normalized.sort()
    signature_bytes = json.dumps(normalized).encode("utf-8")
    return hashlib.sha256(signature_bytes).digest()
