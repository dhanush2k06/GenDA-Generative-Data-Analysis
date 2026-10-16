"""
SQLAlchemy models implementing GenDA's workspace-scoped data architecture.
Every data table uses composite primary keys with `workspace_id` leading,
and child tables use composite foreign keys `(workspace_id, parent_id)`
to enforce tenant isolation at the schema level.
"""

from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    LargeBinary,
    BigInteger,
    Integer,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    JSON,
    Index,
)
from genda.db.engine import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(LargeBinary(16), primary_key=True)
    key_id = Column(String(16), nullable=False, unique=True, index=True)
    key_verifier = Column(LargeBinary(32), nullable=True)  # Cleared on revoke
    wrapped_dek = Column(LargeBinary(96), nullable=True)    # Cleared first on revoke
    status = Column(String(16), nullable=False, default="active")  # 'active', 'revoking', 'revoked'
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class Dataset(Base):
    __tablename__ = "datasets"

    workspace_id = Column(LargeBinary(16), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True)
    id = Column(LargeBinary(16), primary_key=True)
    fingerprint = Column(LargeBinary(32), nullable=False)
    name_enc = Column(LargeBinary(512), nullable=True)
    row_count = Column(BigInteger, nullable=False)
    col_count = Column(Integer, nullable=False)
    profile_enc = Column(LargeBinary, nullable=False)  # Encrypted aggregate profile
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("idx_datasets_fingerprint", "workspace_id", "fingerprint"),
    )


class DatasetColumn(Base):
    __tablename__ = "dataset_columns"

    workspace_id = Column(LargeBinary(16), primary_key=True)
    id = Column(LargeBinary(16), primary_key=True)
    dataset_id = Column(LargeBinary(16), nullable=False)
    col_index = Column(Integer, nullable=False)
    name_enc = Column(LargeBinary, nullable=False)
    name_hash = Column(LargeBinary(32), nullable=False)
    type_class = Column(String(32), nullable=False)
    null_rate_bucket = Column(String(16), nullable=False)
    distinct_ratio_bucket = Column(String(16), nullable=False)
    skew_bucket = Column(String(16), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "dataset_id"],
            ["datasets.workspace_id", "datasets.id"],
            ondelete="CASCADE",
        ),
        Index("idx_columns_dataset", "workspace_id", "dataset_id"),
    )


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    workspace_id = Column(LargeBinary(16), primary_key=True)
    id = Column(LargeBinary(16), primary_key=True)
    dataset_id = Column(LargeBinary(16), nullable=False)
    recipe_id = Column(LargeBinary(16), nullable=True)
    operation = Column(String(64), nullable=False)
    params_enc = Column(LargeBinary, nullable=False)  # Encrypted parameters
    validation_status = Column(String(16), nullable=False)  # 'passed', 'warning', 'failed'
    runtime_ms = Column(Integer, nullable=True)
    library_versions = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "dataset_id"],
            ["datasets.workspace_id", "datasets.id"],
            ondelete="CASCADE",
        ),
        Index("idx_runs_dataset", "workspace_id", "dataset_id"),
    )


class Recipe(Base):
    __tablename__ = "recipes"

    workspace_id = Column(LargeBinary(16), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True)
    id = Column(LargeBinary(16), primary_key=True)
    name_enc = Column(LargeBinary, nullable=False)
    description_enc = Column(LargeBinary, nullable=True)
    spec_json_enc = Column(LargeBinary, nullable=False)  # Encrypted structured spec
    category = Column(String(64), nullable=False)
    version = Column(String(16), nullable=False, default="1.0")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class RecipeOutcome(Base):
    __tablename__ = "recipe_outcomes"

    workspace_id = Column(LargeBinary(16), primary_key=True)
    id = Column(LargeBinary(16), primary_key=True)
    recipe_id = Column(LargeBinary(16), nullable=False)
    dataset_id = Column(LargeBinary(16), nullable=False)
    validation_status = Column(String(16), nullable=False)
    baseline_delta_json = Column(JSON, nullable=False)
    feedback = Column(String(32), nullable=True)  # 'positive', 'negative', 'neutral'
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "recipe_id"],
            ["recipes.workspace_id", "recipes.id"],
            ondelete="CASCADE",
        ),
        Index("idx_outcomes_recipe", "workspace_id", "recipe_id"),
    )


class PurgeJob(Base):
    __tablename__ = "purge_jobs"

    workspace_id = Column(LargeBinary(16), primary_key=True)
    status = Column(String(16), nullable=False, default="pending")  # 'pending', 'running', 'completed', 'failed'
    completed_steps = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True)
    workspace_id = Column(LargeBinary(16), nullable=False, index=True)
    key_id = Column(String(16), nullable=False)
    action = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
