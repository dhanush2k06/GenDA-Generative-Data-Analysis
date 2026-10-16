"""
Repository for recording and querying security audit events.
Strictly records metadata actions; never records dataset cell contents, keys, or secrets.
"""

from __future__ import annotations
import secrets
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from genda.auth.context import WorkspaceContext
from genda.db.models import AuditEvent, utcnow


class AuditRepo:
    def __init__(self, db: Session):
        self.db = db

    def record_event(self, workspace_id: bytes, key_id: str, action: str) -> AuditEvent:
        event = AuditEvent(
            id=secrets.token_hex(16),
            workspace_id=workspace_id,
            key_id=key_id,
            action=action,
            created_at=utcnow(),
        )
        self.db.add(event)
        self.db.commit()
        return event

    def list_events(self, ctx: WorkspaceContext, limit: int = 50) -> List[Dict[str, Any]]:
        events = (
            self.db.query(AuditEvent)
            .filter(AuditEvent.workspace_id == ctx.workspace_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(min(limit, 100))
            .all()
        )
        return [
            {
                "id": e.id,
                "key_id": e.key_id,
                "action": e.action,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]
