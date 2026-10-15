"""
Analysis and profiling routes.
Executes allowlisted operations deterministically with cross-engine validation.
"""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Body

from genda.core.models import (
    AnalysisRequest,
    AnalysisResult,
    DatasetProfile,
)
from genda.core.profiling import profile_dataset
from genda.core.operations import execute_operation, OperationError
from genda.core.charts import build_chart_for_result
from genda.session.store import session_store
from genda.api.security import verify_token

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/session/{session_id}/profile", response_model=DatasetProfile)
async def get_dataset_profile(
    session_id: str,
    token: str = Depends(verify_token),
):
    """
    Profile the session dataset: calculate distributions, null counts, duplicate rows,
    type inferences, and data quality warnings.
    """
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    # Check if profile is already cached
    if session.profile is not None:
        return session.profile

    profile = profile_dataset(session.df)
    session.profile = profile
    return profile


@router.post("/session/{session_id}/analyze", response_model=AnalysisResult)
async def run_analysis(
    session_id: str,
    request: AnalysisRequest = Body(...),
    token: str = Depends(verify_token),
):
    """
    Execute a validated analytical operation on the in-memory dataset.
    Generates evidence-backed result, cross-engine checks, and Plotly chart spec.
    """
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    try:
        result = execute_operation(session.df, request)
    except OperationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Operation failed unexpectedly: {type(e).__name__}",
        )

    # Attach interactive Plotly chart spec
    chart_spec = build_chart_for_result(result)
    result.chart_spec = chart_spec

    # Record in session results history
    session.results.append(result)

    return result


@router.get("/session/{session_id}/results")
async def list_session_results(
    session_id: str,
    token: str = Depends(verify_token),
):
    """List all computed analysis results for this session."""
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    return {"results": session.results, "count": len(session.results)}
