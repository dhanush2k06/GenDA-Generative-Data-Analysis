"""
Tenant isolation tests:
Verifies that Workspace A's stored datasets, columns, recipes, and runs
can never be read, modified, or deleted by Workspace B, even with known IDs.
"""

import pytest
import secrets
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from genda.db.engine import Base
from genda.db.models import Workspace, Dataset, DatasetColumn
from genda.auth.keys import generate_workspace_key
from genda.crypto.envelope import generate_dek, wrap_dek
from genda.auth.context import WorkspaceContext
from genda.db.repositories.workspace_repo import WorkspaceRepo
from genda.db.repositories.dataset_repo import DatasetRepo
from genda.db.repositories.recipe_repo import RecipeRepo
from genda.db.repositories.run_repo import RunRepo


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def create_test_workspace(db, name="ws"):
    full_key, key_id, verifier, kek = generate_workspace_key()
    dek = generate_dek()
    wrapped = wrap_dek(dek, kek, key_id)
    repo = WorkspaceRepo(db)
    ws = repo.create_workspace(key_id, verifier, wrapped)
    ctx = WorkspaceContext(ws.id, key_id, dek, status="active")
    return ws, ctx, full_key


def test_cross_workspace_dataset_isolation(db_session):
    ws_a, ctx_a, _ = create_test_workspace(db_session, "A")
    ws_b, ctx_b, _ = create_test_workspace(db_session, "B")

    dataset_repo = DatasetRepo(db_session)

    # Workspace A saves a dataset
    fp_a = secrets.token_bytes(32)
    profile_a = {
        "columns": [
            {"name": "revenue", "type": "float64", "null_count": 0, "distinct_count": 50},
            {"name": "region", "type": "string", "null_count": 0, "distinct_count": 4, "frequencies": {"North": 25, "South": 25}},
        ]
    }
    cols_a = [
        {"name": "revenue", "type_class": "numeric", "null_rate_bucket": "none", "distinct_ratio_bucket": "high", "skew_bucket": "normal"},
        {"name": "region", "type_class": "categorical", "null_rate_bucket": "none", "distinct_ratio_bucket": "low", "skew_bucket": "normal"},
    ]

    ds_a = dataset_repo.save_dataset(
        ctx=ctx_a,
        dataset_name="Workspace A Confidential Sales",
        fingerprint=fp_a,
        row_count=100,
        col_count=2,
        profile_dict=profile_a,
        columns_data=cols_a,
    )

    # 1. Workspace A can read its dataset
    data_for_a = dataset_repo.get_dataset(ctx_a, ds_a.id)
    assert data_for_a is not None
    assert data_for_a["name"] == "Workspace A Confidential Sales"
    assert len(data_for_a["columns"]) == 2

    # 2. Workspace B attempts to read Workspace A's dataset by ID -> returns None
    data_for_b = dataset_repo.get_dataset(ctx_b, ds_a.id)
    assert data_for_b is None

    # 3. Workspace B lists datasets -> Workspace A's dataset is not present
    list_for_b = dataset_repo.list_datasets(ctx_b)
    assert len(list_for_b) == 0

    # 4. Workspace B attempts to delete Workspace A's dataset -> returns False
    deleted = dataset_repo.delete_dataset(ctx_b, ds_a.id)
    assert deleted is False

    # Dataset A still exists
    assert dataset_repo.get_dataset(ctx_a, ds_a.id) is not None


def test_cross_workspace_recipe_isolation(db_session):
    ws_a, ctx_a, _ = create_test_workspace(db_session, "A")
    ws_b, ctx_b, _ = create_test_workspace(db_session, "B")

    recipe_repo = RecipeRepo(db_session)

    # A saves recipe
    spec = {"operation": "group_sum", "roles": {"group_by": "categorical", "metric": "numeric"}}
    rec_a = recipe_repo.save_recipe(
        ctx=ctx_a,
        name="A's Secret Metric Technique",
        category="finance",
        spec=spec,
    )

    # B cannot fetch A's recipe
    assert recipe_repo.get_recipe(ctx_b, rec_a.id) is None

    # B lists recipes -> empty
    assert len(recipe_repo.list_recipes(ctx_b)) == 0
