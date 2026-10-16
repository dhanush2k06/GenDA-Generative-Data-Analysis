"""
Pydantic schemas for requests, results, profiling, and sessions.
Pure schemas independent of FastAPI.
"""

from __future__ import annotations
from typing import Any, Literal, Union, Annotated
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Analytical Operation Requests (Discriminated Union)
# ---------------------------------------------------------------------------

class GroupSum(BaseModel):
    operation: Literal["group_sum"] = "group_sum"
    group_by: str
    metric: str
    agg: Literal["sum", "mean", "count", "min", "max"] = "sum"


class GroupAgg(BaseModel):
    operation: Literal["group_agg"] = "group_agg"
    group_by: str
    metric: str
    agg: Literal["sum", "mean", "count", "min", "max"] = "sum"


class NumericSummary(BaseModel):
    operation: Literal["numeric_summary"] = "numeric_summary"
    column: str


class MissingSummary(BaseModel):
    operation: Literal["missing_summary"] = "missing_summary"


class FilterCount(BaseModel):
    operation: Literal["filter_count"] = "filter_count"
    column: str
    operator: Literal["==", "!=", ">", ">=", "<", "<=", "contains"]
    value: Any


class DateComparison(BaseModel):
    operation: Literal["date_comparison"] = "date_comparison"
    date_column: str
    metric_column: str
    range_1_start: str
    range_1_end: str
    range_2_start: str
    range_2_end: str
    agg: Literal["sum", "mean", "count"] = "sum"


class CategoryRank(BaseModel):
    operation: Literal["category_rank"] = "category_rank"
    category_column: str
    metric_column: str
    agg: Literal["sum", "mean", "count"] = "sum"
    top_n: int = 10
    ascending: bool = False


AnalysisRequest = Annotated[
    Union[GroupSum, GroupAgg, NumericSummary, MissingSummary, FilterCount, DateComparison, CategoryRank],
    Field(discriminator="operation"),
]


# ---------------------------------------------------------------------------
# Results & Verification
# ---------------------------------------------------------------------------

class AnalysisResult(BaseModel):
    title: str
    operation: str
    inputs: dict[str, Any]
    result: Any
    chart_spec: dict[str, Any] | None = None
    warnings: list[str] = []
    validation_status: Literal["passed", "warning", "failed"] = "passed"
    execution_time_ms: float = 0.0
    cross_engine_match: bool | None = None
    engine_details: str = "Polars v0.20 + DuckDB v0.10 validation"
    evidence_summary: str = ""
    limitations: list[str] = []


# ---------------------------------------------------------------------------
# Profiling Schemas
# ---------------------------------------------------------------------------

class CategoricalFrequency(BaseModel):
    value: str
    count: int
    percentage: float


class ColumnProfile(BaseModel):
    name: str
    inferred_type: Literal["numeric", "categorical", "datetime", "boolean", "text", "unknown"]
    polars_type: str
    total_count: int
    null_count: int
    null_percentage: float
    distinct_count: int
    is_unique: bool
    min_val: Any | None = None
    max_val: Any | None = None
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    q25: float | None = None
    q75: float | None = None
    top_frequencies: list[CategoricalFrequency] = []
    warnings: list[str] = []


class DatasetProfile(BaseModel):
    row_count: int
    column_count: int
    columns: list[ColumnProfile]
    duplicate_rows: int
    memory_bytes: int
    dataset_warnings: list[str] = []


# ---------------------------------------------------------------------------
# Preview & Session Schemas
# ---------------------------------------------------------------------------

class DataPreview(BaseModel):
    session_id: str
    filename: str
    size_bytes: int
    headers: list[str]
    row_count: int
    col_count: int
    preview_rows: list[dict[str, Any]]
    column_types: dict[str, str]
    encoding: str = "utf-8"


class SessionInfo(BaseModel):
    session_id: str
    created_at: float
    filename: str | None = None
    row_count: int = 0
    col_count: int = 0
    operations_count: int = 0
    expires_in_seconds: float = 3600.0


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str = "GenDA Local Analysis Service"
    version: str = "0.2.0"
    loopback_only: bool = True
    session_count: int = 0
    database: dict[str, Any] = Field(default_factory=dict)

