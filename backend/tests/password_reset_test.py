"""Tests for the self-service password-reset (forgot password) flow and the
single-use binding on reset tokens.

Style mirrors basic_auth_test.py: the DB session is mocked for the underlying
logic functions, and the audit/email side-effects are patched at the router
boundary so the endpoint tests need no real database or SMTP server.
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient
from jose import jwt

from main import app
from user.auth import (
    request_password_reset,
    change_password,
    create_reset_token,
    reset_token_fingerprint,
    hash_password,
    ResetTokenInvalidError,
    SECRET_KEY,
    ALGORITHM,
    SCOPE_PASSWORD_RESET,
)
from model.models import User

client = TestClient(app)


# =========================================================================
# Reset-token construction: scope + single-use fingerprint
# =========================================================================

def test_reset_token_embeds_scope_and_fingerprint():
    pw_hash = hash_password("SomeOldP@ss1")
    token = create_reset_token(uuid4().hex, pw_hash)

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["scope"] == SCOPE_PASSWORD_RESET
    assert "role" not in payload  # a reset token must carry no role
    # The fingerprint binds the token to the current password hash.
    assert payload["pfp"] == reset_token_fingerprint(pw_hash)


# =========================================================================
# request_password_reset: anti-enumeration (returns None vs a token)
# =========================================================================

@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_request_reset_unknown_email_returns_none(mock_get_db_session):
    mock_session = Mock()
    mock_session.scalar.return_value = None  # no such account
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    assert await request_password_reset("nobody@finwise.com") is None


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_request_reset_inactive_account_returns_none(mock_get_db_session):
    user = Mock(spec=User)
    user.is_deleted = False
    user.is_active = False  # banned -> not eligible
    mock_session = Mock()
    mock_session.scalar.return_value = user
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    assert await request_password_reset("banned@finwise.com") is None


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_request_reset_active_account_returns_token(mock_get_db_session):
    user = Mock(spec=User)
    user.user_id = uuid4()
    user.username = "resetuser"
    user.email = "reset@finwise.com"
    user.password = hash_password("CurrentP@ss1")
    user.is_deleted = False
    user.is_active = True
    mock_session = Mock()
    mock_session.scalar.return_value = user
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    result = await request_password_reset("reset@finwise.com")
    assert result is not None
    uid, token, username, email = result
    assert uid == user.user_id
    assert username == "resetuser"
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["scope"] == SCOPE_PASSWORD_RESET
    assert payload["pfp"] == reset_token_fingerprint(user.password)


# =========================================================================
# change_password: the single-use fingerprint must match the stored hash
# =========================================================================

def _mock_user_for_change(current_plain="CurrentP@ss1"):
    user = Mock(spec=User)
    user.user_id = uuid4()
    user.username = "resetuser"
    user.email = "reset@finwise.com"
    user.password = hash_password(current_plain)
    user.role = "student"
    user.force_password_reset = True
    user.auth_attempts = 3
    user.is_active = True
    user.is_deleted = False
    user.lockout_timestamp = None
    return user


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_change_password_rejects_stale_fingerprint(mock_get_db_session):
    user = _mock_user_for_change()
    mock_session = Mock()
    mock_session.scalar.return_value = user
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    # Fingerprint of a DIFFERENT hash (as if the password already changed).
    stale_fp = reset_token_fingerprint(hash_password("DifferentP@ss9"))

    with pytest.raises(ResetTokenInvalidError):
        await change_password(
            user.user_id, "BrandNewP@ss2", "BrandNewP@ss2",
            expected_fingerprint=stale_fp,
        )


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_change_password_accepts_matching_fingerprint(mock_get_db_session):
    user = _mock_user_for_change()
    mock_session = Mock()
    mock_session.scalar.return_value = user
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    good_fp = reset_token_fingerprint(user.password)

    token, uid, role = await change_password(
        user.user_id, "BrandNewP@ss2", "BrandNewP@ss2",
        expected_fingerprint=good_fp,
    )
    assert isinstance(token, str) and token
    assert uid == user.user_id
    assert role == "student"
    assert user.force_password_reset is False  # cleared on successful reset


# =========================================================================
# Endpoint: /forgot-password is a generic, non-enumerating oracle
# =========================================================================

@patch("user.auth_router.request_password_reset", new_callable=AsyncMock)
def test_forgot_password_unknown_email_generic_200(mock_request_reset):
    mock_request_reset.return_value = None  # no account

    res = client.post("/api/v1/auth/forgot-password", json={"email": "ghost@finwise.com"})

    assert res.status_code == 200
    assert "if an account exists" in res.json()["detail"].lower()


@patch("user.auth_router._record_password_reset_request")
@patch("user.auth_router.send_password_reset_email")
@patch("user.auth_router.request_password_reset", new_callable=AsyncMock)
def test_forgot_password_known_email_sends_link(mock_request_reset, mock_send, mock_audit):
    uid = uuid4()
    mock_request_reset.return_value = (uid, "tok-xyz-123", "realuser", "real@finwise.com")

    res = client.post("/api/v1/auth/forgot-password", json={"email": "real@finwise.com"})

    # Same generic body as the unknown-email case (anti-enumeration).
    assert res.status_code == 200
    assert "if an account exists" in res.json()["detail"].lower()

    # The reset email was scheduled with a link carrying the one-time token.
    mock_send.assert_called_once()
    called_args = mock_send.call_args.args
    assert called_args[0] == "real@finwise.com"      # to
    assert called_args[1] == "realuser"              # username
    assert "tok-xyz-123" in called_args[2]           # reset link contains the token
    assert "/reset-password?token=" in called_args[2]


def test_change_password_without_token_is_401():
    res = client.post(
        "/api/v1/auth/change-password",
        json={"new_password": "BrandNewP@ss2", "new_password_confirm": "BrandNewP@ss2"},
    )
    assert res.status_code == 401
