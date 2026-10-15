"""
Session management routes: upload, preview, status, and clear session.
"""

from __future__ import annotations
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from starlette.responses import JSONResponse

from genda.core.models import HealthResponse, DataPreview, SessionInfo
from genda.core.loading import load_csv_bytes, LoadError
from genda.session.store import session_store
from genda.api.security import verify_token, get_active_token

router = APIRouter(prefix="/api", tags=["session"])


@router.get("/health", response_model=HealthResponse)
async def get_health():
    """Service health check — verifies loopback service is responding."""
    return HealthResponse(
        status="ok",
        service="GenDA Local Analysis Service",
        version="0.2.0",
        loopback_only=True,
        session_count=session_store.active_count,
    )


@router.get("/auth/verify")
async def verify_auth(token: str = Depends(verify_token)):
    """Verifies that the provided token is valid."""
    return {"status": "authenticated", "valid": True}


@router.post("/session/upload", response_model=DataPreview)
async def upload_csv(
    file: UploadFile = File(...),
    token: str = Depends(verify_token),
):
    """
    Upload CSV file directly to local loopback memory.
    Raw bytes never touch non-local hosts and are not persisted to disk.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file has no filename.")

    # Read bytes into memory
    content = await file.read()

    try:
        df, preview = load_csv_bytes(
            file_bytes=content,
            filename=file.filename,
        )
    except LoadError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process file: {type(e).__name__}",
        )

    # Store in memory session
    session_id = session_store.create_session(df=df, filename=file.filename)
    preview.session_id = session_id

    return preview


@router.get("/session/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: str,
    token: str = Depends(verify_token),
):
    """Retrieve metadata about an active in-memory session."""
    info = session_store.get_session_info(session_id)
    if not info:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    return info


@router.delete("/session/{session_id}")
async def clear_session(
    session_id: str,
    token: str = Depends(verify_token),
):
    """
    Clear session: completely dereferences the DataFrame and cached results from RAM.
    """
    success = session_store.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found or already deleted.")
    return {
        "status": "cleared",
        "message": f"Session {session_id} and all related memory allocations were purged.",
    }
