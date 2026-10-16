"""
Startup and periodic sweeper for interrupted purges and expired workspaces.
Ensures crash-resilience: if the server is killed mid-purge, the sweeper resumes it on reboot.
"""

from __future__ import annotations
import logging
from sqlalchemy.orm import Session
from genda.db.models import Workspace, utcnow
from genda.db.engine import get_session_factory
from genda.workspace.purge import execute_workspace_purge

logger = logging.getLogger("genda.workspace.sweeper")


def run_sweep(db: Session | None = None) -> dict[str, int]:
    """
    Scans for:
    1. Interrupted purges (status == 'revoking')
    2. Expired workspaces (expires_at <= utcnow())
    Purges each and returns counts.
    """
    close_db = False
    if db is None:
        factory = get_session_factory()
        db = factory()
        close_db = True

    try:
        now = utcnow()
        interrupted = db.query(Workspace).filter(Workspace.status == "revoking").all()
        expired = (
            db.query(Workspace)
            .filter(Workspace.status == "active", Workspace.expires_at.is_not(None), Workspace.expires_at <= now)
            .all()
        )

        resumed_count = 0
        expired_count = 0

        for ws in interrupted:
            logger.info(f"Sweeper resuming interrupted purge for workspace {ws.id.hex()} (key: {ws.key_id})")
            try:
                execute_workspace_purge(ws.id, db)
                resumed_count += 1
            except Exception as e:
                logger.error(f"Sweeper failed to complete purge for {ws.id.hex()}: {e}")

        for ws in expired:
            logger.info(f"Sweeper purging expired workspace {ws.id.hex()} (key: {ws.key_id})")
            try:
                execute_workspace_purge(ws.id, db)
                expired_count += 1
            except Exception as e:
                logger.error(f"Sweeper failed to purge expired workspace {ws.id.hex()}: {e}")

        return {"resumed_purges": resumed_count, "expired_purges": expired_count}
    finally:
        if close_db:
            db.close()
