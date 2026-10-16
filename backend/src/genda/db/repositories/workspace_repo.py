"""
Repository for workspace lifecycle operations.
"""

from __future__ import annotations
import secrets
from typing import Optional
from sqlalchemy.orm import Session
from genda.db.models import Workspace, utcnow
from genda.auth.context import WorkspaceContext
from genda.workspace.purge import execute_workspace_purge


class WorkspaceRepo:
    def __init__(self, db: Session):
        self.db = db

    def create_workspace(
        self,
        key_id: str,
        verifier: bytes,
        wrapped_dek: bytes,
        expires_at=None,
    ) -> Workspace:
        """Create a new workspace entry with public key_id, verifier, and wrapped DEK."""
        workspace_id = secrets.token_bytes(16)
        ws = Workspace(
            id=workspace_id,
            key_id=key_id,
            key_verifier=verifier,
            wrapped_dek=wrapped_dek,
            status="active",
            created_at=utcnow(),
            expires_at=expires_at,
            last_seen_at=utcnow(),
        )
        self.db.add(ws)
        self.db.commit()
        self.db.refresh(ws)
        return ws

    def get_workspace(self, ctx: WorkspaceContext) -> Optional[Workspace]:
        """Fetch workspace using verified WorkspaceContext."""
        return (
            self.db.query(Workspace)
            .filter(Workspace.id == ctx.workspace_id, Workspace.key_id == ctx.key_id)
            .first()
        )

    def rotate_key(
        self,
        ctx: WorkspaceContext,
        new_key_id: str,
        new_verifier: bytes,
        new_wrapped_dek: bytes,
    ) -> bool:
        """Rotate key: re-wraps DEK with new KEK and updates key_id and verifier."""
        ws = self.get_workspace(ctx)
        if not ws or ws.status != "active":
            return False

        ws.key_id = new_key_id
        ws.key_verifier = new_verifier
        ws.wrapped_dek = new_wrapped_dek
        self.db.commit()
        return True

    def revoke_workspace(self, ctx: WorkspaceContext) -> dict:
        """Triggers complete 8-step workspace purge and crypto-shredding."""
        return execute_workspace_purge(ctx.workspace_id, self.db)
