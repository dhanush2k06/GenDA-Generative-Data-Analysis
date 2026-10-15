"""
Report generation routes: HTML report preview and downloadable file.
"""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response

from genda.core.reporting import render_html_report
from genda.core.profiling import profile_dataset
from genda.session.store import session_store
from genda.api.security import verify_token

router = APIRouter(prefix="/api", tags=["report"])


@router.get("/session/{session_id}/report/html", response_class=HTMLResponse)
async def get_html_report(
    session_id: str,
    token: str = Depends(verify_token),
):
    """
    Generate and display an interactive self-contained HTML analytical report.
    """
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    # Ensure profile exists
    if session.profile is None:
        session.profile = profile_dataset(session.df)

    html_content = render_html_report(
        filename=session.filename,
        dataset_profile=session.profile,
        results=session.results,
        report_title=f"GenDA Report — {session.filename}",
    )

    return HTMLResponse(content=html_content, status_code=200)


@router.get("/session/{session_id}/report/download")
async def download_html_report(
    session_id: str,
    token: str = Depends(verify_token),
):
    """
    Download the self-contained HTML analytical report.
    """
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    if session.profile is None:
        session.profile = profile_dataset(session.df)

    html_content = render_html_report(
        filename=session.filename,
        dataset_profile=session.profile,
        results=session.results,
        report_title=f"GenDA Report — {session.filename}",
    )

    clean_name = session.filename.replace(".csv", "")
    return Response(
        content=html_content,
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="genda_report_{clean_name}.html"',
        },
    )
