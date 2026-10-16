"""
FastAPI application factory for GenDA local service.
Configures loopback-only binding, CORS allowlists, security middlewares, and routes.
"""

from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from contextlib import asynccontextmanager
from genda.api.security import SecurityHeadersMiddleware, ALLOWED_ORIGINS
from genda.api.routes_session import router as session_router
from genda.api.routes_analysis import router as analysis_router
from genda.api.routes_report import router as report_router
from genda.api.routes_workspace import router as workspace_router
from genda.api.routes_metadata import router as metadata_router
from genda.db.engine import init_db
from genda.workspace.sweeper import run_sweep


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist and sweep interrupted purges/expired keys
    try:
        init_db()
        run_sweep()
    except Exception as e:
        import logging
        logging.getLogger("genda").warning(f"Startup database initialization deferred: {e}")
    yield


def create_app() -> FastAPI:
    """Instantiate and configure the GenDA FastAPI application."""
    app = FastAPI(
        title="GenDA — Generative Data Analyst",
        description="Local-first, privacy-preserving analytical service.",
        version="0.2.0",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )

    # Security headers and loopback enforcement
    app.add_middleware(SecurityHeadersMiddleware)

    # CORS configuration — strict allowlist, never wildcard
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(ALLOWED_ORIGINS),
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(session_router)
    app.include_router(analysis_router)
    app.include_router(report_router)
    app.include_router(workspace_router)
    app.include_router(metadata_router)


    # If built frontend exists, mount it to serve from the exact same loopback origin
    from pathlib import Path
    dist_path = Path(__file__).resolve().parents[4] / "dist"
    if dist_path.exists() and (dist_path / "index.html").exists():
        from fastapi.staticfiles import StaticFiles
        app.mount("/", StaticFiles(directory=str(dist_path), html=True), name="static_frontend")

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        # Prevent leaking raw data rows or sensitive machine paths
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal service error: {type(exc).__name__}"},
        )

    return app


app = create_app()
