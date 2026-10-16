"""
Recipe adaptation and column role binding engine.
Transforms structured technique specifications into concrete executable requests
bound to a new dataset, requiring user confirmation and pre-execution validation.
"""

from __future__ import annotations
from typing import Dict, Any, List, Tuple


class AdaptationError(ValueError):
    """Raised when a recipe cannot be adapted to the target dataset."""
    pass


def adapt_recipe_to_dataset(
    recipe_spec: Dict[str, Any],
    dataset_columns: List[Dict[str, Any]],
    column_mapping: Dict[str, str],
) -> Dict[str, Any]:
    """
    Binds a structured recipe specification to a new dataset's columns.
    Validates that mapped columns exist and fulfill the required type classes.

    Example spec:
    {
      "operation": "group_aggregate",
      "roles": {
        "group_by": {"type_class": "categorical"},
        "metric": {"type_class": "numeric"},
        "agg_func": "mean"
      }
    }
    """
    col_lookup = {c["name"].lower(): c for c in dataset_columns}

    operation = recipe_spec.get("operation")
    if not operation:
        raise AdaptationError("Recipe specification lacks an 'operation' field.")

    roles = recipe_spec.get("roles", {})
    resolved_params: Dict[str, Any] = {}
    validation_notes: List[str] = []

    for role_name, role_def in roles.items():
        if isinstance(role_def, dict) and "type_class" in role_def:
            expected_type = role_def["type_class"]
            # Look up mapping
            target_col_name = column_mapping.get(role_name)
            if not target_col_name:
                raise AdaptationError(f"Missing column mapping for role '{role_name}' ({expected_type}).")

            matched_col = col_lookup.get(target_col_name.lower())
            if not matched_col:
                raise AdaptationError(f"Mapped column '{target_col_name}' does not exist in target dataset.")

            actual_type = matched_col.get("type_class", "unknown")
            if expected_type != "any" and actual_type != expected_type:
                validation_notes.append(
                    f"Warning: Role '{role_name}' expects {expected_type}, but column '{target_col_name}' is {actual_type}."
                )

            resolved_params[role_name] = target_col_name
        else:
            # Fixed parameter (e.g. agg_func, confidence, etc.)
            resolved_params[role_name] = role_def

    return {
        "operation": operation,
        "parameters": resolved_params,
        "validation_notes": validation_notes,
        "is_valid": len([n for n in validation_notes if "Error" in n]) == 0,
    }
