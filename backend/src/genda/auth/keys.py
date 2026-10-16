"""
Workspace key generation, parsing, HKDF derivation, and constant-time verification.
Key format: gk_<key_id>_<secret>
- key_id: 16 hex characters (lookup key)
- secret: 32 bytes urlsafe base64 (256-bit entropy)
"""

from __future__ import annotations
import hmac
import re
import secrets
from typing import Tuple
from genda.crypto.envelope import derive_verifier, derive_kek

# Regex format: gk_<16 hex chars>_<43-44 base64url chars>
KEY_PATTERN = re.compile(r"^gk_([0-9a-fA-F]{16})_([A-Za-z0-9_-]{40,50})$")


class InvalidKeyFormatError(ValueError):
    """Raised when the key string does not match gk_<key_id>_<secret>."""
    pass


def generate_workspace_key() -> Tuple[str, str, bytes, bytes]:
    """
    Generates a new workspace key:
    Returns:
    - full_key: "gk_<key_id>_<secret_str>" (shown to user ONCE)
    - key_id: 16-character public ID string
    - verifier: 32-byte verifier for database storage
    - kek: 32-byte KEK for wrapping the DEK
    """
    key_id = secrets.token_hex(8)  # 16 hex characters
    secret_str = secrets.token_urlsafe(32)  # ~43 chars urlsafe
    secret_bytes = secret_str.encode("utf-8")

    full_key = f"gk_{key_id}_{secret_str}"
    verifier = derive_verifier(secret_bytes, salt=key_id.encode("utf-8"))
    kek = derive_kek(secret_bytes, salt=key_id.encode("utf-8"))

    return full_key, key_id, verifier, kek


def parse_workspace_key(raw_key: str) -> Tuple[str, bytes]:
    """
    Parse a workspace key string.
    Returns: (key_id, secret_bytes)
    Raises InvalidKeyFormatError if format is invalid.
    """
    if not raw_key or not isinstance(raw_key, str):
        raise InvalidKeyFormatError("Empty or non-string key provided.")

    match = KEY_PATTERN.match(raw_key.strip())
    if not match:
        raise InvalidKeyFormatError("Key does not match 'gk_<key_id>_<secret>' format.")

    key_id = match.group(1).lower()
    secret_str = match.group(2)
    return key_id, secret_str.encode("utf-8")


def derive_key_materials(key_id: str, secret_bytes: bytes) -> Tuple[bytes, bytes]:
    """
    Given key_id and secret_bytes, derive both verifier and kek.
    """
    salt = key_id.encode("utf-8")
    verifier = derive_verifier(secret_bytes, salt=salt)
    kek = derive_kek(secret_bytes, salt=salt)
    return verifier, kek


def verify_key(secret_bytes: bytes, key_id: str, stored_verifier: bytes) -> bool:
    """
    Verify the secret against the stored verifier using constant-time comparison.
    """
    derived_verifier = derive_verifier(secret_bytes, salt=key_id.encode("utf-8"))
    return hmac.compare_digest(derived_verifier, stored_verifier)
