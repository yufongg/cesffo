import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from argon2 import PasswordHasher
from uuid import UUID, uuid4

# Import your application components
from main import app  # Your FastAPI instance
from user.auth import (
    request_registration,
    login,
    ExistingUserError,
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


@patch("user.auth_router.verify_registration")
def test_endpoint_register_verify_success(mock_verify_registration):
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
