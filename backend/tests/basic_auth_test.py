import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from argon2 import PasswordHasher
from uuid import UUID, uuid4

# Import your application components
from main import app  # Your FastAPI instance
from user.auth import (
    request_registration,
    login,
    request_password_change_otp,
    verify_password_change_otp,
    resend_password_change_otp,
    hash_password,
    reset_token_fingerprint,
    ExistingUserError,
    InvalidCurrentPasswordError,
    InvalidPasswordChangeOtpError,
    PasswordPolicyError,
    UserNotFoundError,
    PasswordsMismatchError,
    LoginOtpRequiredError,
    InvalidLoginOtpError,
    # DatabaseError
)
from model.models import User

client = TestClient(app)

# =========================================================================
# SECTION 1: UNDERLYING FUNCTION TESTS (Unit & Database Logic Tier)
#
# Signup and login are now two-step (email-OTP) flows:
#   * request_registration() stages a PendingRegistration + returns the code to
#     email out of band. It does NOT create a User and issues NO token.
#   * verify_registration() confirms the code, creates the User and returns a
#     session token.
#   * login() verifies only the password; on success it raises
#     LoginOtpRequiredError (carrying the emailed code) and issues NO token.
#   * verify_login_otp() confirms the code and returns the session token.
# =========================================================================

@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_request_registration_success(mock_get_db_session):
    """request_registration() stages a pending signup and returns (email, username, code)."""
    # 1. Arrange: Mock the SQLAlchemy session lifecycle
    mock_session = Mock()
    mock_session.scalar.return_value = None  # No existing user / pending signup
    # session.query(...).filter(...).delete(...) — opportunistic expired-pending cleanup
    mock_session.query.return_value.filter.return_value.delete.return_value = 0
    # Mock the context manager behavior: with get_db_session() as session
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    # 2. Act: no User is created here; a PendingRegistration is staged instead.
    email, username, code = await request_registration(
        email="test@finwise.com",
        username="testuser",
        password="ValidPassword123!",
        password_confirm="ValidPassword123!",
    )

    # 3. Assert: normalized identity is returned plus a 6-digit code to email out of band.
    assert email == "test@finwise.com"
    assert username == "testuser"
    assert isinstance(code, str) and len(code) == 6 and code.isdigit()
    # The pending row is added and committed (the token/user come later, at verify).
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_request_registration_duplicate_email(mock_get_db_session):
    """request_registration() raises ExistingUserError when the email is already taken."""
    mock_session = Mock()
    # First scalar() lookup (existing User by email blind index) returns a match.
    mock_session.scalar.return_value = User(email="test@finwise.com", username="existing")
    mock_session.query.return_value.filter.return_value.delete.return_value = 0
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    with pytest.raises(ExistingUserError) as exc_info:
        await request_registration("test@finwise.com", "testuser", "Password123!", "Password123!")

    assert exc_info.value.field_taken == "email"


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_login_function_requires_otp_on_correct_password(mock_get_db_session):
    """On a correct password, login() issues NO token — it raises LoginOtpRequiredError
    carrying the emailed second-factor code."""
    # Hash a known password to simulate database state storage
    ph = PasswordHasher()
    hashed_password = ph.hash("SecretPassword123!")

    mock_user = Mock(spec=User)
    mock_user.password = hashed_password
    mock_user.user_id = uuid4()
    mock_user.username = "testuser"
    mock_user.role = "student"
    # concrete values so it takes the happy path instead of tripping the guards.
    mock_user.is_deleted = False
    mock_user.is_active = True
    mock_user.auth_attempts = 0
    mock_user.force_password_reset = False

    mock_session = Mock()
    mock_session.scalar.return_value = mock_user
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    # Argon2 is not configured to need a rehash for the test hash.
    with pytest.raises(LoginOtpRequiredError) as exc_info:
        await login("test@finwise.com", "SecretPassword123!")

    # The challenge carries the details the caller needs to email the code out of band.
    assert exc_info.value.email == "test@finwise.com"
    assert exc_info.value.username == "testuser"
    assert exc_info.value.code.isdigit() and len(exc_info.value.code) == 6


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_login_function_user_not_found(mock_get_db_session):
    """Test login function throws UserNotFoundError when email doesn't exist."""
    mock_session = Mock()
    mock_session.scalar.return_value = None  # Database returns no matching records
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    with pytest.raises(UserNotFoundError):
        await login("missing@finwise.com", "any_password")


# =========================================================================
# SECTION 2: ENDPOINT ROUTER TESTS (HTTP Transport & Validation Tier)
# =========================================================================

@patch("user.auth_router.request_registration")
def test_endpoint_register_step1_success(mock_request_registration):
    """/register stages a pending signup: 200 with a generic message, NO account,
    NO cookie (the account + cookie come at /register/verify)."""
    # request_registration() returns (email, username, code) — the code is emailed, never returned.
    mock_request_registration.return_value = ("newuser@finwise.com", "new_student", "123456")

    payload = {
        "email": "newuser@finwise.com",
        "username": "new_student",
        "password": "SecurePassword123!",
        "password_confirm": "SecurePassword123!",
    }

    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 200
    # No session is established yet, and the code is never leaked to the client.
    assert response.cookies.get("access_token") is None
    assert "123456" not in response.text
    assert "detail" in response.json()


@patch("user.auth_router._record_registration_event")
@patch("user.auth_router.verify_registration")
def test_endpoint_register_verify_success(mock_verify_registration, mock_record_event):
    """/register/verify confirms the emailed code, creating the account and issuing
    the session cookie (auto-login)."""
    # verify_registration() returns (access_token, user_id, role).
    mock_verify_registration.return_value = ("session_token_123", uuid4(), "student")

    payload = {"email": "newuser@finwise.com", "code": "123456"}

    response = client.post("/api/v1/auth/register/verify", json=payload)

    assert response.status_code == 200
    # Token is delivered as an httpOnly cookie, not in the body.
    assert "access_token" not in response.json()
    assert response.cookies.get("access_token") == "session_token_123"
    assert response.json()["user_role"] == "student"
    assert isinstance(UUID(response.json()["user_id"], version=4), UUID)


@patch("user.auth_router.request_registration")
def test_endpoint_register_password_mismatch(mock_request_registration):
    """Test HTTP 400 Bad Request error propagation from internal logic exceptions."""
    mock_request_registration.side_effect = PasswordsMismatchError()

    payload = {
        "email": "user@finwise.com",
        "username": "student",
        "password": "Password1!",
        "password_confirm": "MismatchPassword2!",
    }

    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "Passwords do not match"


# Audit logging is patched out: the endpoint records the login to the real
# append-only audit_log (FK -> user), but this test's user_id is a synthetic
# uuid4() with no backing row, so a real write would hit a FK violation.
@patch("user.auth_router.send_login_code_email")
@patch("user.auth_router._record_login_attempt")
@patch("user.auth_router.login")
def test_endpoint_login_requires_otp(mock_login_logic, mock_record_login, mock_send_code):
    """A correct password no longer logs the user in: /login returns 200 with
    otp_required and NO session cookie — the client must confirm the emailed code."""
    # login() raises LoginOtpRequiredError on a correct password.
    mock_login_logic.side_effect = LoginOtpRequiredError(
        email="active_user@finwise.com", username="active_user", code="654321"
    )

    payload = {"email": "active_user@finwise.com", "password": "CorrectPassword123!"}

    response = client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 200
    assert response.json().get("otp_required") is True
    # No session yet, and the code is never returned to the client (only emailed).
    assert response.cookies.get("access_token") is None
    assert "654321" not in response.text


@patch("user.auth_router._record_login_attempt")
@patch("user.auth_router.verify_login_otp")
def test_endpoint_login_verify_success(mock_verify_otp, mock_record_login):
    """/login/verify confirms the emailed code and issues the session cookie."""
    # verify_login_otp() returns (access_token, user_id, role).
    mock_verify_otp.return_value = ("active_jwt_string", uuid4(), "student")

    payload = {"email": "active_user@finwise.com", "code": "654321"}

    response = client.post("/api/v1/auth/login/verify", json=payload)

    assert response.status_code == 200
    # Token is delivered as an httpOnly cookie, not in the body.
    assert "access_token" not in response.json()
    assert response.cookies.get("access_token") == "active_jwt_string"
    assert response.json()["user_role"] == "student"
    assert isinstance(UUID(response.json()["user_id"], version=4), UUID)


@patch("user.auth_router._record_login_attempt")
@patch("user.auth_router.login")
def test_endpoint_login_invalid_credentials(mock_login_logic, mock_record_login):
    """Test HTTP 401 Unauthorized handling for unauthenticated inputs."""
    mock_login_logic.side_effect = UserNotFoundError()

    payload = {
        "email": "wrong@finwise.com",
        "password": "BadPassword1!",
    }

    response = client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


@patch("user.auth_router._record_login_attempt")
@patch("user.auth_router.verify_login_otp")
def test_endpoint_login_verify_bad_code(mock_verify_otp, mock_record_login):
    """A wrong/expired sign-in code fails generically with 401 and no cookie."""
    mock_verify_otp.side_effect = InvalidLoginOtpError()

    payload = {"email": "active_user@finwise.com", "code": "000000"}

    response = client.post("/api/v1/auth/login/verify", json=payload)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired sign-in code"
    assert response.cookies.get("access_token") is None


def test_endpoint_validation_boundary():
    """Verify built-in Pydantic schema validation captures schema violations without logic hits."""
    payload = {
        "email": "not-an-email",
        "username": "x",  # Too short
        "password": "abc", # Too short
        "password_confirm": "abc"
    }

    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422  # Unprocessable Entity


# =========================================================================
# SECTION 3: LOGGED-IN PASSWORD CHANGE OTP
# =========================================================================

def _password_change_user(current_password="CurrentP@ss1"):
    user = Mock()
    user.user_id = uuid4()
    user.username = "olduser"
    user.email = "localpart@finwise.com"
    user.password = hash_password(current_password)
    user.role = "student"
    user.is_deleted = False
    user.is_active = True
    return user


def _password_change_challenge(user, code="123456"):
    challenge = Mock()
    challenge.user_id = user.user_id
    challenge.code_hash = hash_password(code)
    challenge.code_expires = datetime.now(timezone.utc) + timedelta(minutes=5)
    challenge.attempts = 0
    challenge.sends = 1
    challenge.last_sent_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    challenge.password_fingerprint = reset_token_fingerprint(user.password)
    return challenge


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_request_password_change_otp_success(mock_get_db_session):
    user = _password_change_user()
    mock_session = Mock()
    mock_session.scalar.side_effect = [user, None]
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    email, username, code = await request_password_change_otp(
        user.user_id,
        "CurrentP@ss1",
        "BrandNewP@ss2",
        "BrandNewP@ss2",
    )

    assert email == user.email
    assert username == user.username
    assert code.isdigit() and len(code) == 6
    mock_session.add.assert_called_once()


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_request_password_change_otp_rejects_wrong_current_password(mock_get_db_session):
    user = _password_change_user()
    mock_session = Mock()
    mock_session.scalar.return_value = user
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    with pytest.raises(InvalidCurrentPasswordError):
        await request_password_change_otp(
            user.user_id,
            "WrongP@ss1",
            "BrandNewP@ss2",
            "BrandNewP@ss2",
        )

    mock_session.add.assert_not_called()


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_request_password_change_otp_rejects_username_in_new_password(mock_get_db_session):
    user = _password_change_user()
    mock_session = Mock()
    mock_session.scalar.return_value = user
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    with pytest.raises(PasswordPolicyError) as exc_info:
        await request_password_change_otp(
            user.user_id,
            "CurrentP@ss1",
            "olduserA1!",
            "olduserA1!",
        )

    assert exc_info.value.message == "Password must not contain your username"
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_request_password_change_otp_rejects_email_local_part_in_new_password(mock_get_db_session):
    user = _password_change_user()
    mock_session = Mock()
    mock_session.scalar.return_value = user
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    with pytest.raises(PasswordPolicyError) as exc_info:
        await request_password_change_otp(
            user.user_id,
            "CurrentP@ss1",
            "localpartA1!",
            "localpartA1!",
        )

    assert exc_info.value.message == "Password must not contain your email"
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_request_password_change_otp_rejects_same_password(mock_get_db_session):
    user = _password_change_user()
    mock_session = Mock()
    mock_session.scalar.return_value = user
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    with pytest.raises(PasswordPolicyError) as exc_info:
        await request_password_change_otp(
            user.user_id,
            "CurrentP@ss1",
            "CurrentP@ss1",
            "CurrentP@ss1",
        )

    assert "different from the current one" in exc_info.value.message
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_verify_password_change_otp_success_consumes_challenge(mock_get_db_session):
    user = _password_change_user()
    challenge = _password_change_challenge(user)
    old_password_hash = user.password
    mock_session = Mock()
    mock_session.scalar.side_effect = [user, challenge]
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    await verify_password_change_otp(
        user.user_id,
        "CurrentP@ss1",
        "BrandNewP@ss2",
        "BrandNewP@ss2",
        "123456",
    )

    mock_session.delete.assert_called_once_with(challenge)
    assert user.password != old_password_hash


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_verify_password_change_otp_wrong_code_increments_attempts(mock_get_db_session):
    user = _password_change_user()
    challenge = _password_change_challenge(user)
    mock_session = Mock()
    mock_session.scalar.side_effect = [user, challenge]
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    with pytest.raises(InvalidPasswordChangeOtpError):
        await verify_password_change_otp(
            user.user_id,
            "CurrentP@ss1",
            "BrandNewP@ss2",
            "BrandNewP@ss2",
            "000000",
        )

    assert challenge.attempts == 1
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_verify_password_change_otp_exhausted_challenge_is_burned(mock_get_db_session):
    user = _password_change_user()
    challenge = _password_change_challenge(user)
    challenge.attempts = 5
    mock_session = Mock()
    mock_session.scalar.side_effect = [user, challenge]
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    with pytest.raises(InvalidPasswordChangeOtpError):
        await verify_password_change_otp(
            user.user_id,
            "CurrentP@ss1",
            "BrandNewP@ss2",
            "BrandNewP@ss2",
            "123456",
        )

    mock_session.delete.assert_called_once_with(challenge)


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_verify_password_change_otp_expired_challenge_is_burned(mock_get_db_session):
    user = _password_change_user()
    challenge = _password_change_challenge(user)
    challenge.code_expires = datetime.now(timezone.utc) - timedelta(minutes=1)
    mock_session = Mock()
    mock_session.scalar.side_effect = [user, challenge]
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    with pytest.raises(InvalidPasswordChangeOtpError):
        await verify_password_change_otp(
            user.user_id,
            "CurrentP@ss1",
            "BrandNewP@ss2",
            "BrandNewP@ss2",
            "123456",
        )

    mock_session.delete.assert_called_once_with(challenge)


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_verify_password_change_otp_stale_fingerprint_is_burned(mock_get_db_session):
    user = _password_change_user()
    challenge = _password_change_challenge(user)
    challenge.password_fingerprint = "stale-fingerprint"
    mock_session = Mock()
    mock_session.scalar.side_effect = [user, challenge]
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    with pytest.raises(InvalidPasswordChangeOtpError):
        await verify_password_change_otp(
            user.user_id,
            "CurrentP@ss1",
            "BrandNewP@ss2",
            "BrandNewP@ss2",
            "123456",
        )

    mock_session.delete.assert_called_once_with(challenge)


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_resend_password_change_otp_respects_cooldown(mock_get_db_session):
    user = _password_change_user()
    challenge = _password_change_challenge(user)
    challenge.last_sent_at = datetime.now(timezone.utc)
    mock_session = Mock()
    mock_session.scalar.side_effect = [user, challenge]
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    assert await resend_password_change_otp(user.user_id) is None


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_resend_password_change_otp_respects_max_sends(mock_get_db_session):
    user = _password_change_user()
    challenge = _password_change_challenge(user)
    challenge.sends = 5
    mock_session = Mock()
    mock_session.scalar.side_effect = [user, challenge]
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    assert await resend_password_change_otp(user.user_id) is None


@patch("user.auth_router.send_password_change_code_email")
@patch("user.auth_router.request_password_change_otp")
def test_endpoint_password_change_request_otp_success(mock_request_otp, mock_send_code):
    from user import auth_router

    async def fake_current_user():
        return {"user_id": uuid4().hex, "role": "student"}

    app.dependency_overrides[auth_router.get_current_user] = fake_current_user
    mock_request_otp.return_value = ("active_user@finwise.com", "active_user", "123456")
    try:
        response = client.post(
            "/api/v1/auth/change-my-password/request-otp",
            json={
                "current_password": "CurrentP@ss1",
                "new_password": "BrandNewP@ss2",
                "new_password_confirm": "BrandNewP@ss2",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "123456" not in response.text
    mock_send_code.assert_called_once()


@patch("user.auth_router.request_password_change_otp")
def test_endpoint_password_change_request_otp_wrong_current_password_generic(mock_request_otp):
    from user import auth_router

    async def fake_current_user():
        return {"user_id": uuid4().hex, "role": "student"}

    app.dependency_overrides[auth_router.get_current_user] = fake_current_user
    mock_request_otp.side_effect = InvalidCurrentPasswordError()
    try:
        response = client.post(
            "/api/v1/auth/change-my-password/request-otp",
            json={
                "current_password": "WrongP@ss1",
                "new_password": "BrandNewP@ss2",
                "new_password_confirm": "BrandNewP@ss2",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "Password change request failed"


@patch("user.auth_router.verify_password_change_otp")
def test_endpoint_password_change_confirm_bad_otp_generic(mock_verify_otp):
    from user import auth_router

    async def fake_current_user():
        return {"user_id": uuid4().hex, "role": "student"}

    app.dependency_overrides[auth_router.get_current_user] = fake_current_user
    mock_verify_otp.side_effect = InvalidPasswordChangeOtpError()
    try:
        response = client.post(
            "/api/v1/auth/change-my-password",
            json={
                "current_password": "CurrentP@ss1",
                "new_password": "BrandNewP@ss2",
                "new_password_confirm": "BrandNewP@ss2",
                "code": "000000",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "current password and code" in response.json()["detail"].lower()
