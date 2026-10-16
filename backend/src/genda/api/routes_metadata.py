"""
Metadata capture, dataset viewer, recipe management, and similarity recommendation routes.
Enforces workspace isolation and consent-based opt-in metadata storage.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from genda.auth.context import WorkspaceContext, get_workspace_context
from genda.db.engine import get_db_session
from genda.db.repositories.dataset_repo import DatasetRepo
from genda.db.repositories.recipe_repo import RecipeRepo
from genda.db.repositories.run_repo import RunRepo
from genda.db.repositories.audit_repo import AuditRepo
from genda.session.store import session_store
from genda.core.profiling import profile_dataset
from genda.core.operations import execute_operation, OperationError
from genda.core.models import AnalysisRequest
from genda.similarity.fingerprint import compute_schema_fingerprint, extract_column_features
from genda.similarity.matcher import compare_datasets
from genda.similarity.adapter import adapt_recipe_to_dataset, AdaptationError

router = APIRouter(prefix="/api", tags=["metadata"])


class PersistMetadataRequest(BaseModel):
    consent: bool = Field(..., description="Explicit user consent to persist dataset metadata")
    custom_name: Optional[str] = None


class RecipeCreateRequest(BaseModel):
    name: str
    category: str
    spec: Dict[str, Any]
    description: Optional[str] = ""


class ApplyRecipeRequest(BaseModel):
    recipe_id: str
    column_mapping: Dict[str, str]


@router.post("/session/{session_id}/persist")
async def persist_session_metadata(
    session_id: str,
    req: PersistMetadataRequest = Body(...),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: Session = Depends(get_db_session),
):
    """
    Opt-in endpoint to save dataset fingerprint and aggregate profile metadata.
    Enforces that raw cell values are never stored and categorical frequencies are thresholded.
    """
    if not req.consent:
        raise HTTPException(
            status_code=400,
            detail="Metadata persistence requires explicit user consent ('consent: true').",
        )

    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Active in-memory session not found.")

    # Calculate profile if not present
    if session.profile is None:
        session.profile = profile_dataset(session.df)

    profile_dict = session.profile.model_dump()
    total_rows = session.df.height
    total_cols = session.df.width

    # Extract column features
    columns_data = []
    for col_info in profile_dict.get("columns", []):
        feat = extract_column_features(col_info, total_rows)
        columns_data.append(feat)

    fingerprint = compute_schema_fingerprint(columns_data)
    dataset_name = req.custom_name or session.filename or "Dataset"

    repo = DatasetRepo(db)
    ds = repo.save_dataset(
        ctx=ctx,
        dataset_name=dataset_name,
        fingerprint=fingerprint,
        row_count=total_rows,
        col_count=total_cols,
        profile_dict=profile_dict,
        columns_data=columns_data,
    )

    audit = AuditRepo(db)
    audit.record_event(ctx.workspace_id, ctx.key_id, f"persisted_metadata_{ds.id.hex()[:8]}")

    return {
        "status": "persisted",
        "dataset_id": ds.id.hex(),
        "fingerprint": fingerprint.hex(),
        "name": dataset_name,
        "row_count": total_rows,
        "col_count": total_cols,
    }


@router.get("/metadata/datasets")
async def list_stored_datasets(
    limit: int = 50,
    offset: int = 0,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: Session = Depends(get_db_session),
):
    """List all encrypted datasets metadata stored in the current workspace."""
    repo = DatasetRepo(db)
    items = repo.list_datasets(ctx, limit=limit, offset=offset)
    return {"datasets": items, "count": len(items)}


@router.get("/metadata/datasets/{dataset_id}")
async def get_stored_dataset(
    dataset_id: str,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: Session = Depends(get_db_session),
):
    """Retrieve and decrypt stored dataset profile and structural column metadata."""
    try:
        ds_bytes = bytes.fromhex(dataset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dataset ID format.")

    repo = DatasetRepo(db)
    data = repo.get_dataset(ctx, ds_bytes)
    if not data:
        raise HTTPException(status_code=404, detail="Dataset not found in workspace.")
    return data


@router.delete("/metadata/datasets/{dataset_id}")
async def delete_stored_dataset(
    dataset_id: str,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: Session = Depends(get_db_session),
):
    """Explicitly delete a stored dataset and its child records."""
    try:
        ds_bytes = bytes.fromhex(dataset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid dataset ID format.")

    repo = DatasetRepo(db)
    deleted = repo.delete_dataset(ctx, ds_bytes)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found or already deleted.")
    return {"status": "deleted", "dataset_id": dataset_id}


@router.get("/recipes")
async def list_recipes(
    category: Optional[str] = None,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: Session = Depends(get_db_session),
):
    """List reusable analytical recipes stored in this workspace."""
    repo = RecipeRepo(db)
    recipes = repo.list_recipes(ctx, category=category)
    return {"recipes": recipes, "count": len(recipes)}


@router.post("/recipes")
async def create_recipe(
    req: RecipeCreateRequest = Body(...),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: Session = Depends(get_db_session),
):
    """Save a new structured technique recipe in the workspace library."""
    repo = RecipeRepo(db)
    recipe = repo.save_recipe(
        ctx=ctx,
        name=req.name,
        category=req.category,
        spec=req.spec,
        description=req.description or "",
    )
    return {"status": "created", "recipe_id": recipe.id.hex(), "name": req.name}


@router.get("/session/{session_id}/recommend-recipes")
async def recommend_recipes_for_session(
    session_id: str,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: Session = Depends(get_db_session),
):
    """
    Multi-stage similarity matching:
    Compares the current session dataset against previously stored datasets in the workspace.
    Returns ranked similar datasets with full explanations and matching recipes.
    """
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Active session not found.")

    if session.profile is None:
        session.profile = profile_dataset(session.df)

    profile_dict = session.profile.model_dump()
    source_cols = [
        extract_column_features(col, session.df.height)
        for col in profile_dict.get("columns", [])
    ]
    source_fp = compute_schema_fingerprint(source_cols)

    dataset_repo = DatasetRepo(db)
    stored_summaries = dataset_repo.list_datasets(ctx, limit=50)

    matches = []
    for item in stored_summaries:
        target_id_bytes = bytes.fromhex(item["id"])
        target_details = dataset_repo.get_dataset(ctx, target_id_bytes)
        if not target_details:
            continue

        match = compare_datasets(
            source_fingerprint=source_fp,
            source_cols=source_cols,
            source_row_count=session.df.height,
            target_dataset=target_details,
        )
        if match.composite_score >= 0.40:
            matches.append(match)

    matches.sort(key=lambda m: m.composite_score, reverse=True)

    # Retrieve available recipes
    recipe_repo = RecipeRepo(db)
    recipes = recipe_repo.list_recipes(ctx, limit=20)

    return {
        "matches": [m.to_dict() for m in matches],
        "available_recipes": recipes,
        "source_columns": [c["name"] for c in source_cols],
    }


@router.post("/session/{session_id}/apply-recipe")
async def apply_recipe_to_session(
    session_id: str,
    req: ApplyRecipeRequest = Body(...),
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: Session = Depends(get_db_session),
):
    """
    Applies a reusable recipe to the current dataset.
    Requires user confirmation of column mappings; re-validates before execution.
    """
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Active session not found.")

    try:
        recipe_bytes = bytes.fromhex(req.recipe_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid recipe ID format.")

    recipe_repo = RecipeRepo(db)
    recipe = recipe_repo.get_recipe(ctx, recipe_bytes)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found.")

    # Get dataset column features
    if session.profile is None:
        session.profile = profile_dataset(session.df)
    cols = [
        extract_column_features(c, session.df.height)
        for c in session.profile.model_dump().get("columns", [])
    ]

    try:
        adapted = adapt_recipe_to_dataset(
            recipe_spec=recipe["spec"],
            dataset_columns=cols,
            column_mapping=req.column_mapping,
        )
    except AdaptationError as e:
        raise HTTPException(status_code=400, detail=f"Recipe adaptation error: {str(e)}")

    if not adapted["is_valid"]:
        raise HTTPException(status_code=400, detail=f"Recipe validation failed: {adapted['validation_notes']}")

    # Build analysis request
    analysis_req = AnalysisRequest(
        operation=adapted["operation"],
        parameters=adapted["parameters"],
    )

    try:
        result = execute_operation(session.df, analysis_req)
    except OperationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Log outcome
    run_repo = RunRepo(db)
    run_repo.record_run(
        ctx=ctx,
        dataset_id=bytes(16),  # Session-only or pending dataset ID
        recipe_id=recipe_bytes,
        operation=adapted["operation"],
        params=adapted["parameters"],
        validation_status="passed" if result.evidence.cross_engine_match else "warning",
        runtime_ms=int(result.evidence.execution_time_ms),
        library_versions={"polars": "2.0.0", "duckdb": "1.5.6"},
    )

    return {
        "result": result,
        "adapted_parameters": adapted["parameters"],
        "validation_notes": adapted["validation_notes"],
    }


@router.get("/audit/events")
async def list_audit_events(
    limit: int = 50,
    ctx: WorkspaceContext = Depends(get_workspace_context),
    db: Session = Depends(get_db_session),
):
    """Inspect metadata actions taken within the workspace (no data contents)."""
    repo = AuditRepo(db)
    events = repo.list_events(ctx, limit=limit)
    return {"events": events, "count": len(events)}
