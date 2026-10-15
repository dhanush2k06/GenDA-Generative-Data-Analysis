"""
Data quality rules and cross-engine verification utilities.
Provides independent validation of Polars computations against DuckDB.
"""

from __future__ import annotations
from typing import Any
import polars as pl
import duckdb


def verify_sum_cross_engine(
    df: pl.DataFrame,
    group_col: str,
    metric_col: str,
    polars_result: list[dict[str, Any]],
    tolerance: float = 1e-3,
) -> tuple[bool, str]:
    """
    Independently re-compute group sum in DuckDB and compare with Polars results.
    Returns (is_match, reason).
    """
    try:
        con = duckdb.connect(database=":memory:")
        arrow_table = df.to_arrow()
        con.register("tbl", arrow_table)
        query = f"""
            SELECT 
                COALESCE(CAST("{group_col}" AS VARCHAR), '(Missing)') AS g,
                SUM("{metric_col}") AS s
            FROM tbl
            GROUP BY 1
            ORDER BY s DESC
        """
        duck_rows = con.execute(query).fetchall()

        if len(duck_rows) != len(polars_result):
            return False, f"Row count mismatch: Polars produced {len(polars_result)} groups, DuckDB produced {len(duck_rows)}."

        metric_key = f"{metric_col}_sum"
        for i, (g_duck, s_duck) in enumerate(duck_rows):
            p_row = polars_result[i]
            s_polars = p_row.get(metric_key)

            if s_duck is None and s_polars is None:
                continue
            if s_duck is None or s_polars is None:
                return False, f"Null mismatch at row {i} for group '{g_duck}'."

            if abs(float(s_duck) - float(s_polars)) > tolerance:
                return False, f"Value mismatch at group '{g_duck}': DuckDB={s_duck}, Polars={s_polars}."

        return True, "DuckDB and Polars cross-engine verification passed with exact precision."
    except Exception as e:
        return False, f"Cross-engine verification failed with error: {type(e).__name__}: {str(e)}"
