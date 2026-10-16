"""Initial schema for GenDA workspace metadata and security tables

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-16 16:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'workspaces',
        sa.Column('id', sa.LargeBinary(length=16), nullable=False),
        sa.Column('key_id', sa.String(length=16), nullable=False),
        sa.Column('key_verifier', sa.LargeBinary(length=32), nullable=True),
        sa.Column('wrapped_dek', sa.LargeBinary(length=96), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_id')
    )
    op.create_index('idx_workspaces_key_id', 'workspaces', ['key_id'])

    op.create_table(
        'datasets',
        sa.Column('workspace_id', sa.LargeBinary(length=16), nullable=False),
        sa.Column('id', sa.LargeBinary(length=16), nullable=False),
        sa.Column('fingerprint', sa.LargeBinary(length=32), nullable=False),
        sa.Column('name_enc', sa.LargeBinary(length=512), nullable=True),
        sa.Column('row_count', sa.BigInteger(), nullable=False),
        sa.Column('col_count', sa.Integer(), nullable=False),
        sa.Column('profile_enc', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('workspace_id', 'id')
    )
    op.create_index('idx_datasets_fingerprint', 'datasets', ['workspace_id', 'fingerprint'])

    op.create_table(
        'dataset_columns',
        sa.Column('workspace_id', sa.LargeBinary(length=16), nullable=False),
        sa.Column('id', sa.LargeBinary(length=16), nullable=False),
        sa.Column('dataset_id', sa.LargeBinary(length=16), nullable=False),
        sa.Column('col_index', sa.Integer(), nullable=False),
        sa.Column('name_enc', sa.LargeBinary(), nullable=False),
        sa.Column('name_hash', sa.LargeBinary(length=32), nullable=False),
        sa.Column('type_class', sa.String(length=32), nullable=False),
        sa.Column('null_rate_bucket', sa.String(length=16), nullable=False),
        sa.Column('distinct_ratio_bucket', sa.String(length=16), nullable=False),
        sa.Column('skew_bucket', sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id', 'dataset_id'], ['datasets.workspace_id', 'datasets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('workspace_id', 'id')
    )
    op.create_index('idx_columns_dataset', 'dataset_columns', ['workspace_id', 'dataset_id'])

    op.create_table(
        'recipes',
        sa.Column('workspace_id', sa.LargeBinary(length=16), nullable=False),
        sa.Column('id', sa.LargeBinary(length=16), nullable=False),
        sa.Column('name_enc', sa.LargeBinary(), nullable=False),
        sa.Column('description_enc', sa.LargeBinary(), nullable=True),
        sa.Column('spec_json_enc', sa.LargeBinary(), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('version', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('workspace_id', 'id')
    )

    op.create_table(
        'analysis_runs',
        sa.Column('workspace_id', sa.LargeBinary(length=16), nullable=False),
        sa.Column('id', sa.LargeBinary(length=16), nullable=False),
        sa.Column('dataset_id', sa.LargeBinary(length=16), nullable=False),
        sa.Column('recipe_id', sa.LargeBinary(length=16), nullable=True),
        sa.Column('operation', sa.String(length=64), nullable=False),
        sa.Column('params_enc', sa.LargeBinary(), nullable=False),
        sa.Column('validation_status', sa.String(length=16), nullable=False),
        sa.Column('runtime_ms', sa.Integer(), nullable=True),
        sa.Column('library_versions', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id', 'dataset_id'], ['datasets.workspace_id', 'datasets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('workspace_id', 'id')
    )
    op.create_index('idx_runs_dataset', 'analysis_runs', ['workspace_id', 'dataset_id'])

    op.create_table(
        'recipe_outcomes',
        sa.Column('workspace_id', sa.LargeBinary(length=16), nullable=False),
        sa.Column('id', sa.LargeBinary(length=16), nullable=False),
        sa.Column('recipe_id', sa.LargeBinary(length=16), nullable=False),
        sa.Column('dataset_id', sa.LargeBinary(length=16), nullable=False),
        sa.Column('validation_status', sa.String(length=16), nullable=False),
        sa.Column('baseline_delta_json', sa.JSON(), nullable=False),
        sa.Column('feedback', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id', 'recipe_id'], ['recipes.workspace_id', 'recipes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('workspace_id', 'id')
    )
    op.create_index('idx_outcomes_recipe', 'recipe_outcomes', ['workspace_id', 'recipe_id'])

    op.create_table(
        'purge_jobs',
        sa.Column('workspace_id', sa.LargeBinary(length=16), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('completed_steps', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('workspace_id')
    )

    op.create_table(
        'audit_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.LargeBinary(length=16), nullable=False),
        sa.Column('key_id', sa.String(length=16), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_events_ws', 'audit_events', ['workspace_id'])


def downgrade() -> None:
    op.drop_table('audit_events')
    op.drop_table('purge_jobs')
    op.drop_table('recipe_outcomes')
    op.drop_table('analysis_runs')
    op.drop_table('recipes')
    op.drop_table('dataset_columns')
    op.drop_table('datasets')
    op.drop_table('workspaces')
