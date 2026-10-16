"""
Multi-stage similarity matcher for datasets and recipe recommendations.
Combines exact fingerprinting, structural schema overlap, and profile distribution similarity.
Produces clear, human-readable explanations.
"""

from __future__ import annotations
import difflib
from typing import List, Dict, Any, Tuple


def string_similarity(a: str, b: str) -> float:
    """Fuzzy string similarity ratio using difflib SequenceMatcher."""
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def calculate_jaccard_overlap(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 1.0
    union = len(set_a | set_b)
    if union == 0:
        return 0.0
    return len(set_a & set_b) / union


class SimilarityMatch:
    def __init__(
        self,
        target_dataset_id: str,
        target_name: str,
        composite_score: float,
        stage: str,
        column_match_ratio: float,
        type_compatibility_score: float,
        profile_similarity_score: float,
        explanation: str,
        matched_columns: Dict[str, str],
    ):
        self.target_dataset_id = target_dataset_id
        self.target_name = target_name
        self.composite_score = round(composite_score, 3)
        self.stage = stage
        self.column_match_ratio = round(column_match_ratio, 3)
        self.type_compatibility_score = round(type_compatibility_score, 3)
        self.profile_similarity_score = round(profile_similarity_score, 3)
        self.explanation = explanation
        self.matched_columns = matched_columns

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_dataset_id": self.target_dataset_id,
            "target_name": self.target_name,
            "composite_score": self.composite_score,
            "stage": self.stage,
            "column_match_ratio": self.column_match_ratio,
            "type_compatibility_score": self.type_compatibility_score,
            "profile_similarity_score": self.profile_similarity_score,
            "explanation": self.explanation,
            "matched_columns": self.matched_columns,
        }


def compare_datasets(
    source_fingerprint: bytes,
    source_cols: List[Dict[str, Any]],
    source_row_count: int,
    target_dataset: Dict[str, Any],
) -> SimilarityMatch:
    """
    Compares source dataset against a target dataset across 3 stages.
    """
    target_id = target_dataset["id"]
    target_name = target_dataset["name"]
    target_fp = bytes.fromhex(target_dataset["fingerprint"])
    target_cols = target_dataset.get("columns", [])
    target_row_count = target_dataset.get("row_count", 0)

    # Stage 1: Exact schema match
    if source_fingerprint == target_fp:
        col_map = {c["name"]: c["name"] for c in source_cols}
        return SimilarityMatch(
            target_dataset_id=target_id,
            target_name=target_name,
            composite_score=1.0,
            stage="exact_schema_match",
            column_match_ratio=1.0,
            type_compatibility_score=1.0,
            profile_similarity_score=1.0,
            explanation="Exact schema match: identical column names and data types.",
            matched_columns=col_map,
        )

    # Stage 2: Structural Match
    source_col_dict = {c["name"].lower(): c for c in source_cols}
    target_col_dict = {c["name"].lower(): c for c in target_cols}

    matched_cols: Dict[str, str] = {}
    type_matches = 0
    total_matched = 0

    for s_name, s_col in source_col_dict.items():
        if s_name in target_col_dict:
            t_col = target_col_dict[s_name]
            matched_cols[s_name] = s_name
            total_matched += 1
            if s_col.get("type_class") == t_col.get("type_class"):
                type_matches += 1
        else:
            # Fuzzy match
            best_match = None
            best_sim = 0.0
            for t_name, t_col in target_col_dict.items():
                if t_name not in matched_cols.values():
                    sim = string_similarity(s_name, t_name)
                    if sim > 0.80 and sim > best_sim:
                        best_sim = sim
                        best_match = t_name

            if best_match:
                matched_cols[s_name] = best_match
                total_matched += 1
                if s_col.get("type_class") == target_col_dict[best_match].get("type_class"):
                    type_matches += 1

    col_count_max = max(len(source_cols), len(target_cols), 1)
    col_overlap = total_matched / col_count_max
    type_comp = (type_matches / total_matched) if total_matched > 0 else 0.0

    # Stage 3: Profile Match (distribution & cardinality similarity)
    profile_score = 0.5
    bucket_matches = 0
    total_compared_cols = 0
    for s_name, t_name in matched_cols.items():
        s_col = source_col_dict[s_name]
        t_col = target_col_dict[t_name]
        total_compared_cols += 1
        if s_col.get("null_rate_bucket") == t_col.get("null_rate_bucket"):
            bucket_matches += 0.5
        if s_col.get("distinct_ratio_bucket") == t_col.get("distinct_ratio_bucket"):
            bucket_matches += 0.5

    if total_compared_cols > 0:
        profile_score = bucket_matches / total_compared_cols

    # Composite weighted score: 50% column overlap, 30% type compatibility, 20% profile
    composite = (0.50 * col_overlap) + (0.30 * type_comp) + (0.20 * profile_score)

    explanation = (
        f"Matched {total_matched} of {col_count_max} columns ({int(col_overlap * 100)}% overlap); "
        f"{type_matches} of {total_matched} matched column types are compatible; "
        f"profile distribution similarity is {int(profile_score * 100)}%."
    )

    stage = "structural_match" if composite >= 0.6 else "low_similarity"

    return SimilarityMatch(
        target_dataset_id=target_id,
        target_name=target_name,
        composite_score=composite,
        stage=stage,
        column_match_ratio=col_overlap,
        type_compatibility_score=type_comp,
        profile_similarity_score=profile_score,
        explanation=explanation,
        matched_columns=matched_cols,
    )
