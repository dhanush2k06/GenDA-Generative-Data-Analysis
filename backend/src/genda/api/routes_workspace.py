"""
Workspace lifecycle API routes:
- Create workspace and generate workspace key (shown once)
- Validate workspace key
- Rotate workspace key (re-wrap DEK)
- Revoke workspace (complete 8-step purge with Clear-Site-Data)
"""

from __future__ import annotations
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from genda.auth.keys import generate_workspace_key, derive_key_materials
from genda.crypto.envelope import generate_dek, wrap_dek
from genda.auth.context import WorkspaceContext, get_workspace_context
from genda.db.engine import get_db_session
from genda.db.repositories.workspace_repo import WorkspaceRepo
from genda.db.repositories.dataset_repo import DatasetRepo
from genda.db.repositories.recipe_repo import RecipeRepo
from genda.db.repositories.audit_repo import AuditRepo

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


class WorkspaceCreateResponse(BaseModel):
    workspace_key: str
    key_id: str
    message: str


class WorkspaceStatusResponse(BaseModel):
    status: str
    workspace_id: str
    key_id: str
    datasets_count: int
    recipes_count: int


@router.post("/create", response_model=WorkspaceCreateResponse)
async def create_workspace_endpoint(
    db: Session = Depends(get_db_session),
):
    """
    Generate a new workspace and secret workspace key (gk_<key_id>_<secret>).
    Shown to the user once; server stores only the verifier and wrapped DEK.
    """
    full_key, key_id, verifier, kek = generate_workspace_key()
    dek = generate_dek()
    wrapped_dek = wrap_dek(dek, kek, key_id)

    repo = WorkspaceRepo(db)
    ws = repo.create_workspace(
        key_id=key_id,
        verifier=verifier,
        wrapped_dek=wrapped_dek,
    )

    audit = AuditRepo(db)
    audit.record_event(ws.id, key_id, "workspace_created")

    return WorkspaceCreateResponse(
        workspace_key=full_key,
        key_id=key_id,
        message="Save this key securely now. It is shown only once and cannot be recovered if lost.",
    )


@router.get("/validate", response_model=WorkspaceStatusResponse)
async def validate_workspace(
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: Session = Depends(get_db_session),
):
    """
    Validates workspace key and returns workspace operational status.
    """
    dataset_repo = DatasetRepo(db)
    datasets = dataset_repo.list_datasets(ctx, limit=100)

    recipe_repo = RecipeRepo(db)
    recipes = recipe_repo.list_recipes(ctx, limit=100)

    return WorkspaceStatusResponse(
        status=ctx.status,
        workspace_id=ctx.workspace_id_hex,
        key_id=ctx.key_id,
        datasets_count=len(datasets),
        recipes_count=len(recipes),
    )


@router.post("/rotate", response_model=WorkspaceCreateResponse)
async def rotate_workspace_key(
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: Session = Depends(get_db_session),
):
    """
    Rotates the workspace key: derives a new KEK, re-wraps the in-memory DEK,
    and updates the database verifier and wrapped_dek.
    """
    full_key, new_key_id, new_verifier, new_kek = generate_workspace_key()
    new_wrapped_dek = wrap_dek(ctx.dek, new_kek, new_key_id)

    repo = WorkspaceRepo(db)
    success = repo.rotate_key(ctx, new_key_id, new_verifier, new_wrapped_dek)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to rotate workspace key.")

    audit = AuditRepo(db)
    audit.record_event(ctx.workspace_id, new_key_id, "key_rotated")

    return WorkspaceCreateResponse(
        workspace_key=full_key,
        key_id=new_key_id,
        message="Workspace key successfully rotated. Save your new key immediately.",
    )


@router.post("/revoke")
async def revoke_workspace(
    response: Response,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: Session = Depends(get_db_session),
):
    """
    Complete 8-step workspace revocation and purge:
    Crypto-shreds DEK, dereferences in-memory frames and caches,
    deletes MySQL rows, leaves a tombstone, and instructs client to drop storage.
    """
    repo = WorkspaceRepo(db)
    purge_report = repo.revoke_workspace(ctx)

    # Wipe in-memory DEK immediately
    ctx.wipe()

    # Instruct client browser to clear all cached storage
    response.headers["Clear-Site-Data"] = '"cache", "cookies", "storage"'

    return {
        "status": "revoked",
        "message": "Workspace has been completely purged and crypto-shredded.",
        "purge_report": purge_report,
    }


@router.post("/clear-everything")
async def clear_everything(
    response: Response,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: Session = Depends(get_db_session),
):
    """Emergency action: triggers identical 8-step purge pipeline."""
    return await revoke_workspace(response, ctx, db)
