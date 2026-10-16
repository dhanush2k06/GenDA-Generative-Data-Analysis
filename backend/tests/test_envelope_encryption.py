"""
Tests for envelope encryption, KEK/DEK derivation, and context-bound AES-256-GCM field encryption.
"""

import pytest
import secrets
from genda.crypto.envelope import (
    generate_dek,
    derive_kek,
    derive_verifier,
    wrap_dek,
    unwrap_dek,
    encrypt_field,
    decrypt_field,
    decrypt_field_str,
    DecryptionError,
)
from genda.auth.keys import (
    generate_workspace_key,
    parse_workspace_key,
    verify_key,
    InvalidKeyFormatError,
)


def test_workspace_key_generation_and_parsing():
    full_key, key_id, verifier, kek = generate_workspace_key()

    assert full_key.startswith(f"gk_{key_id}_")
    assert len(key_id) == 16
    assert len(verifier) == 32
    assert len(kek) == 32

    # Parse key
    parsed_id, secret_bytes = parse_workspace_key(full_key)
    assert parsed_id == key_id
    assert len(secret_bytes) > 30

    # Verify key
    assert verify_key(secret_bytes, key_id, verifier) is True

    # Wrong secret or wrong key_id fails verification
    wrong_secret = secrets.token_urlsafe(32).encode("utf-8")
    assert verify_key(wrong_secret, key_id, verifier) is False


def test_invalid_key_formats():
    with pytest.raises(InvalidKeyFormatError):
        parse_workspace_key("invalid_key_string")

    with pytest.raises(InvalidKeyFormatError):
        parse_workspace_key("gk_short_secret")

    with pytest.raises(InvalidKeyFormatError):
        parse_workspace_key("")


def test_dek_wrapping_and_unwrapping():
    dek = generate_dek()
    full_key, key_id, verifier, kek = generate_workspace_key()

    wrapped_dek = wrap_dek(dek, kek, key_id)
    assert len(wrapped_dek) > 32
    assert wrapped_dek != dek

    # Unwrap with correct KEK
    unwrapped = unwrap_dek(wrapped_dek, kek, key_id)
    assert unwrapped == dek

    # Unwrap with wrong KEK fails
    _, _, _, wrong_kek = generate_workspace_key()
    with pytest.raises(DecryptionError):
        unwrap_dek(wrapped_dek, wrong_kek, key_id)

    # Unwrap with wrong key_id fails (bound AAD)
    with pytest.raises(DecryptionError):
        unwrap_dek(wrapped_dek, kek, "0123456789abcdef")


def test_context_bound_field_encryption():
    dek = generate_dek()
    ws_id = secrets.token_bytes(16)
    row_id = secrets.token_bytes(16)
    table = "datasets"
    column = "name_enc"
    plaintext = "Customer Transactions Q3 2024"

    ciphertext = encrypt_field(
        dek=dek,
        plaintext=plaintext,
        workspace_id=ws_id,
        table=table,
        column=column,
        row_id=row_id,
    )
    assert ciphertext != plaintext.encode("utf-8")

    # Decrypt with identical context succeeds
    decrypted_str = decrypt_field_str(
        dek=dek,
        encrypted_data=ciphertext,
        workspace_id=ws_id,
        table=table,
        column=column,
        row_id=row_id,
    )
    assert decrypted_str == plaintext

    # Tampered ciphertext fails
    tampered = bytearray(ciphertext)
    tampered[-1] ^= 0xFF
    with pytest.raises(DecryptionError):
        decrypt_field(dek, bytes(tampered), ws_id, table, column, row_id)

    # Swapped row_id fails
    other_row = secrets.token_bytes(16)
    with pytest.raises(DecryptionError):
        decrypt_field(dek, ciphertext, ws_id, table, column, other_row)

    # Swapped column fails
    with pytest.raises(DecryptionError):
        decrypt_field(dek, ciphertext, ws_id, table, "profile_enc", row_id)

    # Swapped table fails
    with pytest.raises(DecryptionError):
        decrypt_field(dek, ciphertext, ws_id, "recipes", column, row_id)

    # Swapped workspace_id fails (cross-tenant isolation)
    other_ws = secrets.token_bytes(16)
    with pytest.raises(DecryptionError):
        decrypt_field(dek, ciphertext, other_ws, table, column, row_id)
