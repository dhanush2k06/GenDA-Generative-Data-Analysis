"""
WorkspaceContext and FastAPI dependency for workspace authentication.
The WorkspaceContext holds the workspace_id and the decrypted Data Encryption Key (DEK)
in memory only for the duration of the request.
"""

from __future__ import annotations
import ctypes
from typing import Optional
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from genda.auth.keys import parse_workspace_key, derive_key_materials, verify_key, InvalidKeyFormatError
from genda.auth.ratelimit import key_rate_limiter
from genda.crypto.envelope import unwrap_dek, encrypt_field, decrypt_field, decrypt_field_str, DecryptionError
from genda.db.engine import get_db_session
from genda.db.models import Workspace, utcnow

bearer_scheme = HTTPBearer(auto_error=False)


class WorkspaceContext:
    """
    Carries verified workspace identity and ephemeral DEK.
    DEK is kept in RAM only and wiped when explicitly requested.
    """

    def __init__(self, workspace_id: bytes, key_id: str, dek: bytes, status: str = "active"):
        self.workspace_id = workspace_id
        self.key_id = key_id
        self._dek = bytearray(dek)
        self.status = status

    @property
    def dek(self) -> bytes:
        return bytes(self._dek)

    @property
    def workspace_id_hex(self) -> str:
        return self.workspace_id.hex()

    def encrypt(self, plaintext: bytes | str, table: str, column: str, row_id: bytes | str) -> bytes:
        return encrypt_field(
            dek=self.dek,
            plaintext=plaintext,
            workspace_id=self.workspace_id,
            table=table,
            column=column,
            row_id=row_id,
        )

    def decrypt(self, encrypted_data: bytes, table: str, column: str, row_id: bytes | str) -> bytes:
        return decrypt_field(
            dek=self.dek,
            encrypted_data=encrypted_data,
            workspace_id=self.workspace_id,
            table=table,
            column=column,
            row_id=row_id,
        )

    def decrypt_str(self, encrypted_data: bytes, table: str, column: str, row_id: bytes | str) -> str:
        return decrypt_field_str(
            dek=self.dek,
            encrypted_data=encrypted_data,
            workspace_id=self.workspace_id,
            table=table,
            column=column,
            row_id=row_id,
        )

    def wipe(self):
        """Zero out DEK bytes in memory."""
        for i in range(len(self._dek)):
            self._dek[i] = 0


async def get_workspace_context(
    request: Request,
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db_session),
) -> WorkspaceContext:
    """
    Extracts and authenticates workspace key from Authorization header.
    Derives KEK, unwraps DEK, and returns WorkspaceContext.
    """
    raw_token = None
    if auth_header and auth_header.credentials:
        raw_token = auth_header.credentials
    else:
        # Check custom header X-GenDA-Workspace-Key or query param
        raw_token = request.headers.get("X-GenDA-Workspace-Key") or request.query_params.get("workspace_key")

    if not raw_token:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Missing workspace key. Provide via 'Authorization: Bearer gk_...' header.",
        )

    try:
        key_id, secret_bytes = parse_workspace_key(raw_token)
    except InvalidKeyFormatError:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Malformed workspace key format. Must be gk_<key_id>_<secret>.",
        )

    # Check brute-force lockout
    if key_rate_limiter.is_locked(key_id):
        retry_after = int(key_rate_limiter.get_remaining_lockout_seconds(key_id))
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed authentication attempts. Key locked for {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )

    # Lookup workspace tombstone or record
    ws: Optional[Workspace] = db.query(Workspace).filter(Workspace.key_id == key_id).first()

    if not ws:
        key_rate_limiter.record_failure(key_id)
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid workspace key.")

    if ws.status == "revoked":
        raise HTTPException(status_code=410, detail="Workspace has been revoked and purged.")

    if ws.status == "revoking":
        raise HTTPException(status_code=409, detail="Workspace is undergoing revocation and purge.")

    if not ws.key_verifier or not ws.wrapped_dek:
        raise HTTPException(status_code=401, detail="Workspace crypto material has been shredded.")

    # Constant-time verifier check
    if not verify_key(secret_bytes, key_id, ws.key_verifier):
        key_rate_limiter.record_failure(key_id)
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid workspace key.")

    # Successful authentication
    key_rate_limiter.record_success(key_id)

    # Derive KEK and unwrap DEK
    _, kek = derive_key_materials(key_id, secret_bytes)
    try:
        dek = unwrap_dek(ws.wrapped_dek, kek, key_id)
    except DecryptionError:
        raise HTTPException(status_code=500, detail="Cryptographic error: Unable to unwrap workspace DEK.")

    # Update last seen timestamp
    ws.last_seen_at = utcnow()
    db.commit()

    return WorkspaceContext(
        workspace_id=ws.id,
        key_id=key_id,
        dek=dek,
        status=ws.status,
    )


async def get_optional_workspace_context(
    request: Request,
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db_session),
) -> Optional[WorkspaceContext]:
    """Dependency that returns WorkspaceContext if provided, or None if omitted."""
    raw_token = None
    if auth_header and auth_header.credentials:
        raw_token = auth_header.credentials
    else:
        raw_token = request.headers.get("X-GenDA-Workspace-Key") or request.query_params.get("workspace_key")

    if not raw_token:
        return None

    try:
        return await get_workspace_context(request, auth_header, db)
    except HTTPException:
        return None
