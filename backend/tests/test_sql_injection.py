"""
SQL Injection verification tests:
Tests repository and query interfaces with an extensive SQL injection payload corpus:
classic, stacked statements, union-based, and second-order injection through untrusted CSV column names.
"""

import pytest
import secrets
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from genda.db.engine import Base
from genda.db.models import Workspace, Dataset
from genda.auth.keys import generate_workspace_key
from genda.crypto.envelope import generate_dek, wrap_dek
from genda.auth.context import WorkspaceContext
from genda.db.repositories.workspace_repo import WorkspaceRepo
from genda.db.repositories.dataset_repo import DatasetRepo
from genda.db.repositories.recipe_repo import RecipeRepo
from genda.db.repositories.run_repo import RunRepo

INJECTION_PAYLOADS = [
    "' OR '1'='1",
    "admin'--",
    "1; DROP TABLE datasets; --",
    "'; DROP TABLE workspaces; --",
    "1' UNION SELECT 1, 'injected', 3, 4, 5, 6, 7, 8 --",
    "x' AND 1=1 --",
    "test' OR 1=1#",
    "' UNION ALL SELECT NULL,NULL,NULL,NULL--",
    "sleep(5)#",
    "1' WAITFOR DELAY '0:0:5'--",
    "'; EXEC xp_cmdshell('dir'); --",
    "Robert'); DROP TABLE Students;--",
]


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_sql_injection_payloads_in_dataset_repo(db_session):
    full_key, key_id, verifier, kek = generate_workspace_key()
    dek = generate_dek()
    wrapped = wrap_dek(dek, kek, key_id)
    ws_repo = WorkspaceRepo(db_session)
    ws = ws_repo.create_workspace(key_id, verifier, wrapped)
    ctx = WorkspaceContext(ws.id, key_id, dek, status="active")

    dataset_repo = DatasetRepo(db_session)

    # Test each injection payload as dataset_name and untrusted column name
    for idx, payload in enumerate(INJECTION_PAYLOADS):
        fp = secrets.token_bytes(32)
        profile = {
            "columns": [
                {"name": payload, "type": "string", "null_count": 0, "distinct_count": 10}
            ]
        }
        cols = [
            {
                "name": payload,
                "type_class": "categorical",
                "null_rate_bucket": "none",
                "distinct_ratio_bucket": "low",
                "skew_bucket": "normal",
            }
        ]

        # Should safely store without executing injection or raising SQL syntax errors
        ds = dataset_repo.save_dataset(
            ctx=ctx,
            dataset_name=payload,
            fingerprint=fp,
            row_count=50,
            col_count=1,
            profile_dict=profile,
            columns_data=cols,
        )

        assert ds is not None

        # Fetch and verify decrypted content exactly equals the raw payload string
        fetched = dataset_repo.get_dataset(ctx, ds.id)
        assert fetched is not None
        assert fetched["name"] == payload
        assert fetched["columns"][0]["name"] == payload

    # Verify workspaces and datasets tables are intact (not dropped)
    total_datasets = db_session.query(Dataset).count()
    assert total_datasets == len(INJECTION_PAYLOADS)
    total_workspaces = db_session.query(Workspace).count()
    assert total_workspaces == 1


def test_sql_injection_payloads_in_recipe_repo(db_session):
    full_key, key_id, verifier, kek = generate_workspace_key()
    dek = generate_dek()
    wrapped = wrap_dek(dek, kek, key_id)
    ws = WorkspaceRepo(db_session).create_workspace(key_id, verifier, wrapped)
    ctx = WorkspaceContext(ws.id, key_id, dek, status="active")

    recipe_repo = RecipeRepo(db_session)

    for payload in INJECTION_PAYLOADS:
        recipe = recipe_repo.save_recipe(
            ctx=ctx,
            name=payload,
            category=payload,
            spec={"operation": "group_sum", "roles": {"column": payload}},
            description=payload,
        )
        assert recipe is not None

        fetched = recipe_repo.get_recipe(ctx, recipe.id)
        assert fetched is not None
        assert fetched["name"] == payload
        assert fetched["spec"]["roles"]["column"] == payload
