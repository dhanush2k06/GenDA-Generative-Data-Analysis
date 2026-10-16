"""
Envelope encryption and authenticated column encryption with context binding.
Uses AES-256-GCM and HKDF-SHA256 from the Python `cryptography` library.
"""

from __future__ import annotations
import os
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidTag


class CryptoError(Exception):
    """Base exception for cryptographic operations."""
    pass


class DecryptionError(CryptoError):
    """Raised when ciphertext cannot be authenticated or decrypted."""
    pass


def generate_dek() -> bytes:
    """Generate a random 256-bit Data Encryption Key (DEK)."""
    return secrets.token_bytes(32)


def derive_kek(secret_bytes: bytes, salt: bytes | None = None) -> bytes:
    """
    Derive a 256-bit Key Encryption Key (KEK) from the workspace secret using HKDF.
    Label info=b'genda_kek_v1'.
    """
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt or b"genda_workspace_kek_salt",
        info=b"genda_kek_v1",
    )
    return hkdf.derive(secret_bytes)


def derive_verifier(secret_bytes: bytes, salt: bytes | None = None) -> bytes:
    """
    Derive a 256-bit verifier from the workspace secret using HKDF.
    Label info=b'genda_verify_v1'.
    Because this info label is distinct from KEK, the stored verifier
    cannot decrypt or derive the KEK or DEK.
    """
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt or b"genda_workspace_verify_salt",
        info=b"genda_verify_v1",
    )
    return hkdf.derive(secret_bytes)


def wrap_dek(dek: bytes, kek: bytes, key_id: str) -> bytes:
    """
    Wrap the DEK with AES-256-GCM using the KEK.
    Associated data is bound to the key_id.
    Output: 12-byte nonce + ciphertext (including 16-byte tag).
    """
    if len(dek) != 32:
        raise ValueError("DEK must be exactly 32 bytes (256 bits).")
    if len(kek) != 32:
        raise ValueError("KEK must be exactly 32 bytes (256 bits).")

    nonce = os.urandom(12)
    aesgcm = AESGCM(kek)
    ciphertext = aesgcm.encrypt(nonce, dek, key_id.encode("utf-8"))
    return nonce + ciphertext


def unwrap_dek(wrapped_dek: bytes, kek: bytes, key_id: str) -> bytes:
    """
    Unwrap the DEK using the derived KEK.
    Verifies that the wrapped DEK was created for key_id.
    """
    if len(wrapped_dek) < 28:  # 12 nonce + at least 16 tag
        raise DecryptionError("Invalid wrapped DEK payload length.")

    nonce = wrapped_dek[:12]
    ciphertext = wrapped_dek[12:]
    aesgcm = AESGCM(kek)
    try:
        dek = aesgcm.decrypt(nonce, ciphertext, key_id.encode("utf-8"))
        if len(dek) != 32:
            raise DecryptionError("Unwrapped DEK is not 32 bytes.")
        return dek
    except InvalidTag:
        raise DecryptionError("Failed to unwrap DEK: invalid key or corrupted data.")


def build_aad(workspace_id: bytes | str, table: str, column: str, row_id: bytes | str) -> bytes:
    """
    Build bound Associated Authenticated Data (AAD) string.
    Ensures that ciphertext cannot be copied or spliced between:
    - different workspaces
    - different tables
    - different columns
    - different rows
    """
    ws_str = workspace_id.hex() if isinstance(workspace_id, bytes) else str(workspace_id)
    row_str = row_id.hex() if isinstance(row_id, bytes) else str(row_id)
    return f"{ws_str}:{table}:{column}:{row_str}".encode("utf-8")


def encrypt_field(
    dek: bytes,
    plaintext: bytes | str,
    workspace_id: bytes | str,
    table: str,
    column: str,
    row_id: bytes | str,
) -> bytes:
    """
    Encrypt a sensitive field with the in-memory DEK using AES-256-GCM.
    Binds the ciphertext to the workspace, table, column, and row_id.
    Returns: 12-byte nonce + ciphertext + 16-byte tag.
    """
    if isinstance(plaintext, str):
        data = plaintext.encode("utf-8")
    else:
        data = plaintext

    nonce = os.urandom(12)
    aad = build_aad(workspace_id, table, column, row_id)
    aesgcm = AESGCM(dek)
    ciphertext = aesgcm.encrypt(nonce, data, aad)
    return nonce + ciphertext


def decrypt_field(
    dek: bytes,
    encrypted_data: bytes,
    workspace_id: bytes | str,
    table: str,
    column: str,
    row_id: bytes | str,
) -> bytes:
    """
    Decrypt a sensitive field using the in-memory DEK with context validation.
    Raises DecryptionError if tampering, row-swapping, or column-swapping is detected.
    """
    if len(encrypted_data) < 28:
        raise DecryptionError("Encrypted payload too short.")

    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]
    aad = build_aad(workspace_id, table, column, row_id)
    aesgcm = AESGCM(dek)

    try:
        return aesgcm.decrypt(nonce, ciphertext, aad)
    except InvalidTag:
        raise DecryptionError("Ciphertext integrity check failed: data altered or context mismatched.")


def decrypt_field_str(
    dek: bytes,
    encrypted_data: bytes,
    workspace_id: bytes | str,
    table: str,
    column: str,
    row_id: bytes | str,
) -> str:
    """Decrypt field and decode as UTF-8 string."""
    return decrypt_field(dek, encrypted_data, workspace_id, table, column, row_id).decode("utf-8")
