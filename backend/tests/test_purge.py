"""
Purge and revocation verification tests:
Verifies crypto-shredding, memory dereferencing, cache/temp clearing,
database cascading row deletion, verification assertion, and crash recovery.
"""

import pytest
import secrets
from pathlib import Path
import tempfile
import polars as pl
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from genda.db.engine import Base
from genda.db.models import Workspace, Dataset, DatasetColumn, AnalysisRun, Recipe, PurgeJob
from genda.auth.keys import generate_workspace_key
from genda.crypto.envelope import generate_dek, wrap_dek
from genda.auth.context import WorkspaceContext
from genda.db.repositories.workspace_repo import WorkspaceRepo
from genda.db.repositories.dataset_repo import DatasetRepo
from genda.db.repositories.recipe_repo import RecipeRepo
from genda.workspace.registry import resource_registry
from genda.workspace.purge import execute_workspace_purge
from genda.workspace.sweeper import run_sweep


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_complete_workspace_purge_and_crypto_shredding(db_session):
    full_key, key_id, verifier, kek = generate_workspace_key()
    dek = generate_dek()
    wrapped = wrap_dek(dek, kek, key_id)

    ws_repo = WorkspaceRepo(db_session)
    ws = ws_repo.create_workspace(key_id, verifier, wrapped)
    ctx = WorkspaceContext(ws.id, key_id, dek, status="active")

    # 1. Populate DB records
    dataset_repo = DatasetRepo(db_session)
    recipe_repo = RecipeRepo(db_session)

    ds = dataset_repo.save_dataset(
        ctx=ctx,
        dataset_name="Purge Candidate Dataset",
        fingerprint=secrets.token_bytes(32),
        row_count=100,
        col_count=1,
        profile_dict={"columns": [{"name": "col_1", "type": "int64"}]},
        columns_data=[{"name": "col_1", "type_class": "numeric", "null_rate_bucket": "none", "distinct_ratio_bucket": "high", "skew_bucket": "normal"}],
    )
    rec = recipe_repo.save_recipe(
        ctx=ctx,
        name="Purge Candidate Recipe",
        category="general",
        spec={"operation": "group_sum"},
    )

    # 2. Populate ResourceRegistry (in-memory sessions, temp files)
    temp_dir = Path(tempfile.mkdtemp())
    temp_file = temp_dir / "temp_chart.png"
    temp_file.write_text("dummy binary chart data")

    resource_registry.register_temp_dir(ws.id, temp_dir)
    resource_registry.register_temp_file(ws.id, temp_file)

    dummy_df = pl.DataFrame({"a": [1, 2, 3]})
    resource_registry.register_session(ws.id, "sess_123", dummy_df)

    assert resource_registry.has_workspace(ws.id) is True
    assert temp_file.exists() is True

    # 3. Execute Complete Purge
    report = execute_workspace_purge(ws.id, db_session)

    assert report["final_status"] == "revoked"
    assert "crypto_shredded" in report["steps_completed"]
    assert "verification_passed" in report["steps_completed"]

    # 4. Verify Crypto-shredding: wrapped_dek and key_verifier are destroyed
    reloaded_ws = db_session.query(Workspace).filter(Workspace.id == ws.id).first()
    assert reloaded_ws is not None
    assert reloaded_ws.status == "revoked"
    assert reloaded_ws.wrapped_dek is None
    assert reloaded_ws.key_verifier is None
    assert reloaded_ws.revoked_at is not None

    # 5. Verify database data rows are 0
    assert db_session.query(Dataset).filter(Dataset.workspace_id == ws.id).count() == 0
    assert db_session.query(DatasetColumn).filter(DatasetColumn.workspace_id == ws.id).count() == 0
    assert db_session.query(Recipe).filter(Recipe.workspace_id == ws.id).count() == 0

    # 6. Verify ResourceRegistry and files are purged
    assert resource_registry.has_workspace(ws.id) is False
    assert temp_file.exists() is False


def test_crash_recovery_sweeper(db_session):
    full_key, key_id, verifier, kek = generate_workspace_key()
    dek = generate_dek()
    wrapped = wrap_dek(dek, kek, key_id)

    ws_repo = WorkspaceRepo(db_session)
    ws = ws_repo.create_workspace(key_id, verifier, wrapped)
    ctx = WorkspaceContext(ws.id, key_id, dek, status="active")

    # Save a dataset
    dataset_repo = DatasetRepo(db_session)
    dataset_repo.save_dataset(
        ctx=ctx,
        dataset_name="Interrupted Dataset",
        fingerprint=secrets.token_bytes(32),
        row_count=10,
        col_count=1,
        profile_dict={"columns": [{"name": "col_1", "type": "int64"}]},
        columns_data=[{"name": "col_1", "type_class": "numeric", "null_rate_bucket": "none", "distinct_ratio_bucket": "high", "skew_bucket": "normal"}],
    )

    # Simulate process crash midway: status set to 'revoking'
    ws.status = "revoking"
    db_session.commit()

    # Sweeper runs on reboot
    sweep_results = run_sweep(db_session)
    assert sweep_results["resumed_purges"] == 1

    # Verify workspace is now fully revoked and data is gone
    reloaded = db_session.query(Workspace).filter(Workspace.id == ws.id).first()
    assert reloaded.status == "revoked"
    assert reloaded.wrapped_dek is None
    assert db_session.query(Dataset).filter(Dataset.workspace_id == ws.id).count() == 0
