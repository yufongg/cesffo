import hashlib
import hmac
import os
import secrets
import string
from argon2 import PasswordHasher, Type, exceptions
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from jose import jwt
from pydantic import EmailStr
from sqlalchemy import select
from typing import Optional, Tuple
from uuid import UUID

from core import account_lockout

from common.encryption import blind_index
from db.db import get_db_session
from model.models import User

# Username policy mirrors the registration schema (router-level Field bounds).
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 150


SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    if os.getenv("APP_ENV", "development") == "production":
        raise RuntimeError("JWT_SECRET_KEY must be set in production")
    SECRET_KEY = secrets.token_urlsafe(64)

ALGORITHM = "HS256"

#$ Token / lockout lifetimes (minutes, except the attempt count). Tuned to the security NFRs.
ACCESS_TOKEN_EXPIRE_MINUTES = 30    # how long a normal session token is valid
RESET_TOKEN_EXPIRE_MINUTES = 10     # forced-reset token issued at login
RESET_LINK_EXPIRE_MINUTES = 30      # self-service "forgot password" link
MAX_AUTH_ATTEMPTS = 5               # failed logins before the account locks

# Token scopes keep a reset token from ever being used as a normal session token.
SCOPE_ACCESS = "access"
SCOPE_PASSWORD_RESET = "password_reset"  # nosec B105

# --- Canonical roles (lowercase everywhere to avoid authz drift) ---
ROLE_STUDENT = "student"
ROLE_INSTRUCTOR = "instructor"
ROLE_ADMIN = "admin"
ALLOWED_ROLES = frozenset({ROLE_STUDENT, ROLE_INSTRUCTOR, ROLE_ADMIN})

# --- Password policy (SR-01) ---
# Minimum 8 chars AND at least one uppercase, one lowercase, one digit and one
# special character. Strength here comes from the enforced character-class
# complexity (plus the known-bad blocklist and the username/email-substring
# checks below as defence-in-depth) rather than from raw length alone.
MIN_PASSWORD_LENGTH = 8
# Cap at 128 to bound Argon2 work (DoS guard) while still permitting passphrases.
# This MUST match the router schema's max_length.
MAX_PASSWORD_LENGTH = 128
# Characters accepted as "special" for the SR-01 complexity check. Kept broad so
# password managers and generated temp passwords can satisfy the rule.
SPECIAL_CHARS = "!@#$%^&*()-_=+[]{};:,.<>?/|~`\"'\\"

# Single shared hasher instance (thread-safe). Parameters are pinned explicitly to
# satisfy SR-02 (Argon2id, 64 MiB memory, 3 iterations, parallelism 4) instead of
# relying on argon2-cffi's library defaults, which can change between versions.
_ph = PasswordHasher(
    time_cost=3,          # iterations (SR-02: >= 3)
    memory_cost=65536,    # 64 MiB expressed in KiB (SR-02: >= 64MB)
    parallelism=4,        # lanes (SR-02: 4)
    hash_len=32,
    salt_len=16,
    type=Type.ID,         # Argon2id (SR-02)
)

# Precomputed hash of a throwaway value. We verify against this when an email
# is not found so that "user missing" and "wrong password" take the same time,
# closing the login timing side-channel used for account enumeration.
_DUMMY_HASH = _ph.hash("timing-equalizer-not-a-real-password")

AUTH_SUCCESS = "Authentication Success"
AUTH_FAILURE = "Authentication Failed"

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


class InvalidCurrentPasswordError(Exception):
    """Raised when a logged-in user's supplied current password is wrong."""
    pass


class ResetTokenInvalidError(Exception):
    """Raised when a password-reset token no longer matches the account state —
    e.g. it was already used (the password changed) or the password was changed
    by another path. Gives the stateless reset token single-use semantics."""
    pass


def hash_password(password: str) -> str:
    """Hash a plaintext password with Argon2id."""
    return _ph.hash(password)


def generate_temp_password(length: int = 16) -> str:
    """Generate a cryptographically strong temporary password that satisfies the
    SR-01 policy (length + all four character classes).

    Uses secrets (CSPRNG) and guarantees at least one uppercase, lowercase, digit
    and special character so the value always passes validate_password_strength().
    """
    length = max(length, MIN_PASSWORD_LENGTH)
    pools = (string.ascii_uppercase, string.ascii_lowercase, string.digits, SPECIAL_CHARS)
    # One guaranteed character from each required class, then fill from the union.
    chars = [secrets.choice(pool) for pool in pools]
    alphabet = "".join(pools)
    chars += [secrets.choice(alphabet) for _ in range(length - len(chars))]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def validate_password_strength(password: str, *, username: str = "", email: str = "") -> None:
    #! SR-01: length + character-class rules first, then the defence-in-depth
    #! blocklist and "must not contain your own username/email" checks.
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordPolicyError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise PasswordPolicyError(f"Max allowed password length is {MAX_PASSWORD_LENGTH} characters long")
    if not any(c.isupper() for c in password):
        raise PasswordPolicyError("Password must include at least one uppercase letter")
    if not any(c.islower() for c in password):
        raise PasswordPolicyError("Password must include at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        raise PasswordPolicyError("Password must include at least one number")
    if not any(c in SPECIAL_CHARS for c in password):
        raise PasswordPolicyError("Password must include at least one special character")
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


def reset_token_fingerprint(password_hash: str) -> str:
    """Derive a short, one-way fingerprint of the user's CURRENT password hash,
    keyed by the server secret. Embedded in a reset token (claim ``pfp``) and
    re-checked when the token is spent: once the password changes, the stored hash
    changes, so the fingerprint no longer matches and the token is rejected. This
    gives the stateless JWT single-use behaviour without any server-side denylist.
    The raw password hash is never exposed — only this keyed digest."""
    return hmac.new(SECRET_KEY.encode(), password_hash.encode(), hashlib.sha256).hexdigest()[:32]


def create_reset_token(
    user_id: str, password_hash: str, expires_minutes: int = RESET_TOKEN_EXPIRE_MINUTES
) -> str:
    """A short-lived token authorising exactly one action: choosing a new
    password. It carries no role, is rejected by every normal endpoint, and is
    bound to the current password hash so it can only be used once."""
    payload = {
        "sub": user_id,
        "scope": SCOPE_PASSWORD_RESET,
        "pfp": reset_token_fingerprint(password_hash),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


async def register(email: EmailStr, username: str, password: str, password_confirm: str) -> Tuple[str, UUID, str]:
    if password != password_confirm:
        raise PasswordsMismatchError()

    email = email.strip().lower()
    username = username.strip()

    #! Enforce the password policy before touching the DB or hashing (cheap reject first).
    validate_password_strength(password, username=username, email=email)

    with get_db_session() as session:
        #? Uniqueness checks: email by blind index (it's encrypted), username by value.
        if session.scalar(select(User).where(User.email_bidx == blind_index(email))):
            raise ExistingUserError("email")

        if session.scalar(select(User).where(User.username == username)):
            raise ExistingUserError("username")

        hashed_password = hash_password(password)

        try:
            user = User(
                email=email,
                email_bidx=blind_index(email),
                username=username,
                password=hashed_password,
                role=ROLE_STUDENT,  # self-service signup can NEVER pick its own role (privilege-escalation guard)
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            token = create_access_token(user.user_id.hex, user.role)
            return token, user.user_id, user.role
        except Exception:
            raise DatabaseError()


async def login(email: EmailStr, password: str) -> Tuple[str, UUID, str]:
    email = email.strip().lower()
    with get_db_session() as session:
        #? email is encrypted at rest, so we look it up by its deterministic blind index.
        existing_user = session.scalar(select(User).where(User.email_bidx == blind_index(email)))

        #! No such user: still run a real Argon2 verify against a throwaway hash so this
        #! path takes the same time as a wrong-password attempt (closes the timing oracle
        #! an attacker would use to enumerate which emails exist), then fail generically.
        if not existing_user:
            try:
                _ph.verify(_DUMMY_HASH, password)
            except Exception:  # nosec B110
                pass
            raise UserNotFoundError()

        #! Banned or soft-deleted accounts must never authenticate.
        if existing_user.is_deleted or not existing_user.is_active:
            raise InactiveAccountError()

        if existing_user.auth_attempts >= MAX_AUTH_ATTEMPTS:
            if account_lockout(existing_user.username):
                raise AccountLockedError()


        try:
            _ph.verify(existing_user.password, password)
        except exceptions.VerifyMismatchError:
            #! Wrong password: bump the failed-attempt counter (feeds the lockout) and fail generically.
            existing_user.auth_attempts += 1
            session.commit()
            raise PasswordsMismatchError()
        except (exceptions.InvalidHashError, exceptions.VerificationError):
            raise HTTPException(status_code=500, detail="Internal authentication error")

        #* Correct password: clear the failed-attempt counter.
        existing_user.auth_attempts = 0

        #* If our Argon2 cost parameters have since changed, transparently re-hash on this login.
        if _ph.check_needs_rehash(existing_user.password):
            existing_user.password = _ph.hash(password)

        #^ Snapshot what we need now, before the context manager commits and closes the session.
        must_reset = existing_user.force_password_reset
        uid = existing_user.user_id
        role = existing_user.role
        pwd_hash = existing_user.password


    if must_reset:
        raise PasswordResetRequiredError(create_reset_token(uid.hex, pwd_hash))

    token = create_access_token(uid.hex, role)
    return token, uid, role


async def update_profile(
    user_id: UUID, *, username: str | None = None, email: EmailStr | None = None
) -> Tuple[str, EmailStr, str]:
    """Update the username and/or email for the logged-in user.

    Returns the resulting (username, email, role) after the change. Enforces the
    same normalization and uniqueness rules as registration: email is lowercased
    and looked up / deduplicated via its blind index (it is encrypted at rest),
    username is trimmed and length-checked. Raises ExistingUserError on a clash
    and UserNotFoundError if the account no longer exists.
    """
    if username is not None:
        username = username.strip()
        if not (USERNAME_MIN_LENGTH <= len(username) <= USERNAME_MAX_LENGTH):
            raise PasswordPolicyError(
                f"Username must be between {USERNAME_MIN_LENGTH} and {USERNAME_MAX_LENGTH} characters"
            )
    if email is not None:
        email = email.strip().lower()

    with get_db_session() as session:
        user = session.scalar(select(User).where(User.user_id == user_id))
        if not user:
            raise UserNotFoundError()

        if username is not None and username != user.username:
            clash = session.scalar(
                select(User).where(User.username == username, User.user_id != user_id)
            )
            if clash:
                raise ExistingUserError("username")
            user.username = username

        if email is not None and email != user.email:
            new_bidx = blind_index(email)
            clash = session.scalar(
                select(User).where(User.email_bidx == new_bidx, User.user_id != user_id)
            )
            if clash:
                raise ExistingUserError("email")
            user.email = email
            user.email_bidx = new_bidx

        try:
            session.commit()
            session.refresh(user)
        except Exception:
            raise DatabaseError()

        return user.username, user.email, user.role


async def change_password_authenticated(
    user_id: UUID, current_password: str, new_password: str, new_password_confirm: str
) -> None:
    """Rotate the password for a logged-in user who proves knowledge of their
    current password. Unlike change_password() this does NOT consume a reset
    token — the caller is already authenticated via their session cookie.

    Raises InvalidCurrentPasswordError if the current password is wrong,
    PasswordsMismatchError if the confirmation differs, and PasswordPolicyError
    if the new password fails the policy or matches the current one.
    """
    if new_password != new_password_confirm:
        raise PasswordsMismatchError()

    with get_db_session() as session:
        user = session.scalar(select(User).where(User.user_id == user_id))
        if not user:
            raise UserNotFoundError()

        # Prove knowledge of the existing password before allowing a change.
        try:
            _ph.verify(user.password, current_password)
        except exceptions.VerifyMismatchError:
            raise InvalidCurrentPasswordError()
        except (exceptions.InvalidHashError, exceptions.VerificationError):
            raise HTTPException(status_code=500, detail="Internal authentication error")

        # Same policy as registration (length, blocklist, not username/email).
        validate_password_strength(new_password, username=user.username, email=user.email)

        # Forbid a no-op "change" back to the same password.
        if current_password == new_password:
            raise PasswordPolicyError("New password must be different from the current one")

        user.password = hash_password(new_password)


async def request_password_reset(email: EmailStr) -> Optional[Tuple[UUID, str, str, str]]:
    """Self-service "forgot password": look up an account by email and, if it is
    eligible to sign in, mint a one-time reset token for it.

    Returns ``(user_id, reset_token, username, email)`` when a deliverable account
    exists, or ``None`` otherwise (unknown / banned / soft-deleted). The CALLER
    MUST return an identical generic response in both cases so the endpoint does
    not become an account-enumeration oracle. Crucially, the user's existing
    password is left untouched — nothing changes until they complete the reset."""
    email = email.strip().lower()
    with get_db_session() as session:
        user = session.scalar(select(User).where(User.email_bidx == blind_index(email)))
        if not user or user.is_deleted or not user.is_active:
            return None
        token = create_reset_token(user.user_id.hex, user.password, RESET_LINK_EXPIRE_MINUTES)
        return user.user_id, token, user.username, user.email


async def change_password(
    user_id: UUID,
    new_password: str,
    new_password_confirm: str,
    expected_fingerprint: Optional[str] = None,
) -> Tuple[str, UUID, str]:
    """Rotate the password for a user who authenticated via a reset token.
    Clears the force-reset flag and any lockout, then issues a real session.

    ``expected_fingerprint`` is the ``pfp`` claim carried by the reset token; it
    must still match the stored password hash, otherwise the token has already
    been spent (or the password changed since it was issued) and is rejected."""
    if new_password != new_password_confirm:
        raise PasswordsMismatchError()

    with get_db_session() as session:
        user = session.scalar(select(User).where(User.user_id == user_id))
        if not user:
            raise UserNotFoundError()

        if not user.is_active or user.is_deleted:
            raise ResetTokenInvalidError()

        # Single-use guard: the token is bound to the password hash it was minted
        # against. Reject a replayed/stale token in constant time.
        if expected_fingerprint is not None and not hmac.compare_digest(
            expected_fingerprint, reset_token_fingerprint(user.password)
        ):
            raise ResetTokenInvalidError()

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
        user.lockout_timestamp = None
        uid = user.user_id
        role = user.role

    return create_access_token(uid.hex, role), uid, role
