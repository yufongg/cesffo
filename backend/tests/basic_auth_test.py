import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from argon2 import PasswordHasher
from uuid import UUID, uuid4

# Import your application components
from main import app  # Your FastAPI instance
from user.auth import (
    register, 
    login, 
    ExistingUserError, 
    UserNotFoundError, 
    PasswordsMismatchError, 
    # DatabaseError
)
from model.models import User

client = TestClient(app)

# =========================================================================
# SECTION 1: UNDERLYING FUNCTION TESTS (Unit & Database Logic Tier)
# =========================================================================

@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_register_function_success(mock_get_db_session):
    """Test underlying register function with complete valid state parameters."""
    # 1. Arrange: Mock the SQLAlchemy session lifecycle
    mock_session = Mock()
    mock_session.scalar.return_value = None  # No existing user found (email/username unique)
    def mock_refresh_side_effect(target_obj):
        target_obj.user_id = uuid4()
        return None
    mock_session.refresh.side_effect = mock_refresh_side_effect
    # Mock the context manager behavior: with get_db_session() as session
    mock_get_db_session.return_value.__enter__.side_effect = [mock_session, mock_session, mock_session]

    # 2. Act: Execute function
    token, user_id = await register(
        email=  "test@finwise.com",
        username="testuser",
        password="ValidPassword123!",
        password_confirm="ValidPassword123!"
    )

    # 3. Assert: Verify database interactions and output formats
    assert isinstance(token, str)  #
    assert isinstance(user_id, UUID)
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_register_function_duplicate_email(mock_get_db_session):
    """Test that register function throws ExistingUserError when email exists."""
    mock_session = Mock()
    mock_session.scalar.return_value = User(email="test@finwise.com", username="existing")
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    with pytest.raises(ExistingUserError) as exc_info:
        await register("test@finwise.com", "testuser", "Password123!", "Password123!")
    
    assert exc_info.value.field_taken == "email"


@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_login_function_success(mock_get_db_session):
    """Test underlying login function verifies hashes and authenticates successfully."""
    # Hash a known password to simulate database state storage
    ph = PasswordHasher()
    hashed_password = ph.hash("SecretPassword123!")
    
    mock_user = Mock(spec=User)
    mock_user.password = hashed_password
    mock_user.user_id = uuid4()

    mock_session = Mock()
    mock_session.scalar.return_value = mock_user
    mock_get_db_session.return_value.__enter__.return_value = mock_session

    token, user_id = await login("test@finwise.com", "SecretPassword123!")

    assert token == ""
    assert isinstance(user_id, UUID)


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

@patch("user.auth_router.register")
def test_endpoint_register_success(mock_register_logic):
    """Test HTTP 201 Created behavior when underlying registration completes."""
    # Mock the internal logic: register() returns (access_token, user_id, role).
    mock_register_logic.return_value = ("session_token_123", uuid4(), "student")

    payload = {
        "email": "newuser@finwise.com",
        "username": "new_student",
        "password": "SecurePassword123!",
        "password_confirm": "SecurePassword123!"
    }

    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 201
    # Token is delivered as an httpOnly cookie, not in the body.
    assert "access_token" not in response.json()
    assert response.cookies.get("access_token") == "session_token_123"
    assert response.json()["user_role"] == "student"
    assert isinstance(UUID(response.json()["user_id"], version=4), UUID)


@patch("user.auth_router.register")
def test_endpoint_register_password_mismatch(mock_register_logic):
    """Test HTTP 400 Bad Request error propagation from internal logic exceptions."""
    mock_register_logic.side_effect = PasswordsMismatchError()

    payload = {
        "email": "user@finwise.com",
        "username": "student",
        "password": "Password1!",
        "password_confirm": "MismatchPassword2!"
    }

    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "Passwords do not match"


@patch("user.auth_router.login")
def test_endpoint_login_success(mock_login_logic):
    """Test HTTP 200 OK authorization handling for legitimate credentials."""
    # login() returns (access_token, user_id, role).
    mock_login_logic.return_value = ("active_jwt_string", uuid4(), "student")

    payload = {
        "email": "active_user@finwise.com",
        "password": "CorrectPassword123!"
    }

    response = client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 200
    # Token is delivered as an httpOnly cookie, not in the body.
    assert "access_token" not in response.json()
    assert response.cookies.get("access_token") == "active_jwt_string"
    assert response.json()["user_role"] == "student"
    assert isinstance(UUID(response.json()["user_id"], version=4), UUID)


@patch("user.auth_router.login")
def test_endpoint_login_invalid_credentials(mock_login_logic):
    """Test HTTP 401 Unauthorized handling for unauthenticated inputs."""
    mock_login_logic.side_effect = UserNotFoundError()

    payload = {
        "email": "wrong@finwise.com",
        "password": "BadPassword1!"
    }

    response = client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


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