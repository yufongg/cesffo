import os
import secrets
from argon2 import PasswordHasher, exceptions
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from jose import jwt
from pydantic import EmailStr
from sqlalchemy import select
from typing import Tuple
from uuid import UUID

from core import account_lockout

from db.db import get_db_session
from model.models import User


SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    if os.getenv("APP_ENV", "development") == "production":
        raise RuntimeError("JWT_SECRET_KEY must be set in production")
    SECRET_KEY = secrets.token_urlsafe(64)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

RESET_TOKEN_EXPIRE_MINUTES = 10
MAX_AUTH_ATTEMPTS = 5

# Token scopes keep a reset token from ever being used as a normal session token.
SCOPE_ACCESS = "access"
SCOPE_PASSWORD_RESET = "password_reset"

# --- Canonical roles (lowercase everywhere to avoid authz drift) ---
ROLE_STUDENT = "student"
ROLE_INSTRUCTOR = "instructor"
ROLE_ADMIN = "admin"
ALLOWED_ROLES = frozenset({ROLE_STUDENT, ROLE_INSTRUCTOR, ROLE_ADMIN})

# --- Password policy (NIST SP 800-63B aligned: length first, block known-bad) ---
MIN_PASSWORD_LENGTH = 8
# NIST 800-63B says verifiers SHALL allow at least 64 chars. We cap at 128 to
# bound Argon2 work (DoS guard) while still permitting passphrases. This MUST
# match the router schema's max_length.
MAX_PASSWORD_LENGTH = 128

# Single shared hasher instance (thread-safe).
_ph = PasswordHasher()

# Precomputed hash of a throwaway value. We verify against this when an email
# is not found so that "user missing" and "wrong password" take the same time,
# closing the login timing side-channel used for account enumeration.
_DUMMY_HASH = _ph.hash("timing-equalizer-not-a-real-password")

# A tiny illustrative blocklist. In production, check against the Have I Been
# Pwned k-anonymity API (send only the first 5 SHA-1 chars) or a local copy.
COMMON_PASSWORDS = {
    "password", "password1", "password123", "123456", "12345678",
    "qwerty", "letmein", "admin", "welcome", "iloveyou", "abc123",
    "changeme", "passw0rd",
}


class ExistingUserError(Exception):
    def __init__(self, field_taken):
        super().__init__()
        self.field_taken = field_taken

class UserNotFoundError(Exception):
    pass

class PasswordsMismatchError(Exception):
    pass

class DatabaseError(Exception):
    pass

class AccountLockedError(Exception):
    pass

class InactiveAccountError(Exception):
    """Raised when a banned or soft-deleted account attempts to log in."""
    pass

class PasswordPolicyError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class PasswordResetRequiredError(Exception):

    def __init__(self, reset_token: str):
        super().__init__()
        self.reset_token = reset_token


def hash_password(password: str) -> str:
    """Hash a plaintext password with Argon2id."""
    return _ph.hash(password)


def generate_temp_password(length: int = 16) -> str:
    """Generate a cryptographically strong temporary password.

    Uses secrets (CSPRNG). URL-safe alphabet avoids ambiguous shell/HTML chars.
    """
    return secrets.token_urlsafe(length)


def parse_user_id(raw: str) -> UUID:
    """Parse a user id (hex or canonical form) into a UUID, or raise ValueError."""
    return UUID(raw)


def validate_password_strength(password: str, *, username: str = "", email: str = "") -> None:
    
    #! Password strength is using the NEW NIST as defined in slides.
    #! IIRC it is at least 8 char, no need for special char and or digits. but need to check against common dictionary passwords
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordPolicyError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise PasswordPolicyError(f"Max allowed password length is {MAX_PASSWORD_LENGTH} characters long")
    if password.lower() in COMMON_PASSWORDS:
        raise PasswordPolicyError("Password is too common; please choose a less predictable one")
    
    lowered = password.lower()
    if username and username.lower() in lowered:
        raise PasswordPolicyError("Password must not contain your username")
    if email and email.split("@")[0].lower() in lowered:
        raise PasswordPolicyError("Password must not contain your email")


def create_access_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "scope": SCOPE_ACCESS,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_reset_token(user_id: str) -> str:
    """A short-lived token authorising exactly one action: choosing a new
    password. It carries no role and is rejected by every normal endpoint."""
    payload = {
        "sub": user_id,
        "scope": SCOPE_PASSWORD_RESET,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


async def register(email: EmailStr, username: str, password: str, password_confirm: str) -> Tuple[str, UUID, str]:
    if password != password_confirm:
        raise PasswordsMismatchError()

    email = email.strip().lower()
    username = username.strip()

    #! Enforce password policy before touching the DB or hashing
    validate_password_strength(password, username=username, email=email)

    with get_db_session() as session:
        if session.scalar(select(User).where(User.email == email)):
            raise ExistingUserError("email")

        if session.scalar(select(User).where(User.username == username)):
            raise ExistingUserError("username")

        hashed_password = hash_password(password)

        #^ ONLY if the email and usernames are unique will the new account be created using hte ORM.
        try:

            #^ This creates a new user object. Because this object is NEWLY created and does not exists in ,
            #^ when the .commit method is called, the database will know its an insert
            user = User(
                email=email,
                username=username,
                password=hashed_password,
                role=ROLE_STUDENT,  # self-service signup can NEVER pick its own role (privilege-escalation guard)
            )
            session.add(user)
            session.commit()

            #^ I think this just flushes
            session.refresh(user)

            token = create_access_token(user.user_id.hex, user.role)
            return token, user.user_id, user.role
        except Exception:
            raise DatabaseError()


async def login(email: EmailStr, password: str) -> Tuple[str, UUID, str]:
    email = email.strip().lower()
    with get_db_session() as session:
        existing_user = session.scalar(select(User).where(User.email == email))

        # Argon2 verify against a dummy hash so the response time matches the
        # "wrong password" path, then fail with the same generic error.
        if not existing_user:
            try:
                _ph.verify(_DUMMY_HASH, password)
            except Exception:
                raise UserNotFoundError()

        # Banned or soft-deleted accounts must never authenticate.
        if existing_user.is_deleted or not existing_user.is_active:
            raise InactiveAccountError()

        if existing_user.auth_attempts >= MAX_AUTH_ATTEMPTS:
            if account_lockout(existing_user.username):
                raise AccountLockedError()


        try:
            _ph.verify(existing_user.password, password)
        except exceptions.VerifyMismatchError:
            existing_user.auth_attempts += 1
            session.commit()
            raise PasswordsMismatchError()
        except (exceptions.InvalidHashError, exceptions.VerificationError):
            raise HTTPException(status_code=500, detail="Internal authentication error")

        # Successful login: reset the failed-attempt counter.
        existing_user.auth_attempts = 0

        # Transparently upgrade the stored hash if Argon2 parameters changed.
        if _ph.check_needs_rehash(existing_user.password):
            existing_user.password = _ph.hash(password)

        # Capture what we need before the session commits and closes.
        must_reset = existing_user.force_password_reset
        uid = existing_user.user_id
        role = existing_user.role


    if must_reset:
        raise PasswordResetRequiredError(create_reset_token(uid.hex))

    token = create_access_token(uid.hex, role)
    return token, uid, role


async def change_password(
    user_id: UUID, new_password: str, new_password_confirm: str
) -> Tuple[str, UUID, str]:
    """Rotate the password for a user who authenticated via a reset token.
    Clears the force-reset flag and any lockout, then issues a real session."""
    if new_password != new_password_confirm:
        raise PasswordsMismatchError()

    with get_db_session() as session:
        user = session.scalar(select(User).where(User.user_id == user_id))
        if not user:
            raise UserNotFoundError()

        # Same policy as registration (length, blocklist, not username/email).
        validate_password_strength(new_password, username=user.username, email=user.email)

        # Don't let them "rotate" straight back to the temporary password.
        try:
            _ph.verify(user.password, new_password)
            raise PasswordPolicyError("New password must be different from the current one")
        except exceptions.VerifyMismatchError:
            pass  # good — the new password differs from the old one

        user.password = hash_password(new_password)
        user.force_password_reset = False
        user.auth_attempts = 0
        uid = user.user_id
        role = user.role

    return create_access_token(uid.hex, role), uid, role
