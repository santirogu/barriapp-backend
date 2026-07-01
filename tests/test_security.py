"""Unit tests for password hashing and JWT (no DB)."""

import pytest

from app.core.security import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


@pytest.mark.req("A-3")
def test_password_hash_roundtrip() -> None:
    hashed = hash_password("s3cret-pass")
    assert hashed != "s3cret-pass"
    assert verify_password("s3cret-pass", hashed)
    assert not verify_password("wrong-pass", hashed)


@pytest.mark.req("A-3")
def test_access_token_carries_subject_and_roles() -> None:
    token = create_access_token("507f1f77bcf86cd799439011", ["client", "seller"])
    payload = decode_token(token)
    assert payload["sub"] == "507f1f77bcf86cd799439011"
    assert payload["type"] == ACCESS_TOKEN_TYPE
    assert payload["roles"] == ["client", "seller"]


@pytest.mark.req("A-3")
def test_refresh_token_type() -> None:
    payload = decode_token(create_refresh_token("507f1f77bcf86cd799439011"))
    assert payload["type"] == REFRESH_TOKEN_TYPE
    assert "roles" not in payload
