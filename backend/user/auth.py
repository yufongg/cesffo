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
from sqlalchemy.exc import IntegrityError
from typing import Optional, Tuple
from uuid import UUID

from core import account_lockout

from common.encryption import blind_index
from db.db import get_db_session
from model.models import User, PendingRegistration, LoginChallenge

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

#$ Email-verification (registration 2FA) settings.
VERIFICATION_CODE_EXPIRE_MINUTES = 10       # how long an emailed 6-digit code stays valid
MAX_VERIFICATION_ATTEMPTS = 5               # wrong-code guesses before the pending signup is burned
VERIFICATION_RESEND_COOLDOWN_SECONDS = 60   # min gap between code emails (anti inbox-bombing)

#$ Login two-factor (login 2FA) settings. Mirrors the registration code above:
#$ same lifetime, guess cap and resend cooldown, applied to the login challenge.
LOGIN_OTP_EXPIRE_MINUTES = VERIFICATION_CODE_EXPIRE_MINUTES
MAX_LOGIN_OTP_ATTEMPTS = MAX_VERIFICATION_ATTEMPTS
LOGIN_OTP_RESEND_COOLDOWN_SECONDS = VERIFICATION_RESEND_COOLDOWN_SECONDS

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

class InvalidVerificationError(Exception):
    """Raised for any bad/expired/exhausted/unknown email-verification code. A
    single generic failure so the verify endpoint can't be used to probe which
    signups are currently pending."""
    pass

class LoginOtpRequiredError(Exception):
    """Raised by login() once the password is verified: authentication is not yet
    complete because a second factor (emailed 6-digit code) is owed. Carries the
    details the caller needs to email that code out of band; NO session token is
    issued until the code is confirmed via verify_login_otp()."""
    def __init__(self, email: str, username: str, code: str):
        super().__init__()
        self.email = email
        self.username = username
        self.code = code

class InvalidLoginOtpError(Exception):
    """Raised for any bad/expired/exhausted/unknown login OTP. A single generic
    failure so the verify endpoint can't be used to probe accounts."""
    pass

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


def generate_verification_code() -> str:
    #* 6-digit numeric code from a CSPRNG (secrets), zero-padded so "000123" is valid.
    return f"{secrets.randbelow(1_000_000):06d}"


async def request_registration(
    email: EmailStr, username: str, password: str, password_confirm: str
) -> Tuple[str, str, str]:
    """Step 1 of signup: validate the details and stage a pending registration
    guarded by an emailed 6-digit code. NO User row is created here — the account
    only comes into existence once the code is confirmed (see verify_registration).

    Returns ``(email, username, code)`` so the caller can send the code out of
    band; the code is NEVER returned to the client. Raises PasswordsMismatchError,
    PasswordPolicyError, or ExistingUserError (email/username already taken)."""
    if password != password_confirm:
        raise PasswordsMismatchError()

    email = email.strip().lower()
    username = username.strip()

    #! Enforce the password policy before touching the DB or hashing (cheap reject first).
    validate_password_strength(password, username=username, email=email)

    email_bidx = blind_index(email)
    code = generate_verification_code()

    with get_db_session() as session:
        #* Opportunistic cleanup: drop expired pending signups so abandoned ones
        #* don't permanently squat on a username/email.
        session.query(PendingRegistration).filter(
            PendingRegistration.code_expires < datetime.now(timezone.utc)
        ).delete(synchronize_session=False)

        #? Uniqueness against real accounts: email by blind index (it's encrypted), username by value.
        if session.scalar(select(User).where(User.email_bidx == email_bidx)):
            raise ExistingUserError("email")
        if session.scalar(select(User).where(User.username == username)):
            raise ExistingUserError("username")
        #? A different in-flight signup already holding this username blocks it too.
        if session.scalar(
            select(PendingRegistration).where(
                PendingRegistration.username == username,
                PendingRegistration.email_bidx != email_bidx,
            )
        ):
            raise ExistingUserError("username")

        #* Overwrite any prior pending signup for THIS email (re-register / issue a fresh code).
        existing = session.scalar(
            select(PendingRegistration).where(PendingRegistration.email_bidx == email_bidx)
        )
        if existing:
            session.delete(existing)
            session.flush()

        now = datetime.now(timezone.utc)
        pending = PendingRegistration(
            email_bidx=email_bidx,
            username=username,
            password_hash=hash_password(password),
            code_hash=hash_password(code),   #! store only the Argon2 hash of the code, never the code itself
            code_expires=now + timedelta(minutes=VERIFICATION_CODE_EXPIRE_MINUTES),
            attempts=0,
            last_sent_at=now,
        )
        session.add(pending)
        try:
            session.commit()
        except IntegrityError:
            #! Lost a race on the unique(email_bidx)/unique(username) constraint.
            raise ExistingUserError("username")

    return email, username, code


async def verify_registration(email: EmailStr, code: str) -> Tuple[str, UUID, str]:
    """Step 2 of signup: confirm the emailed code and, only if it matches, create
    the real User (auto-logging them in with a session token). The code is
    single-use, time-limited, and capped at MAX_VERIFICATION_ATTEMPTS guesses.

    Returns ``(access_token, user_id, role)`` on success. Raises
    InvalidVerificationError for any bad/expired/exhausted/unknown code (one
    generic failure — no enumeration oracle), or ExistingUserError if the
    email/username got taken between step 1 and now."""
    email = email.strip().lower()
    email_bidx = blind_index(email)

    with get_db_session() as session:
        pending = session.scalar(
            select(PendingRegistration).where(PendingRegistration.email_bidx == email_bidx)
        )

        #! Unknown signup: still burn the same Argon2 time as a real check so
        #! "no pending" and "wrong code" are indistinguishable by timing.
        if pending is None:
            try:
                _ph.verify(_DUMMY_HASH, code)
            except Exception:  # nosec B110
                pass
            raise InvalidVerificationError()

        now = datetime.now(timezone.utc)
        expires = pending.code_expires
        if expires.tzinfo is None:               # tolerate a naive value from the DB driver
            expires = expires.replace(tzinfo=timezone.utc)

        #! Expired or out of guesses: burn the pending signup — a fresh code must
        #! be requested. Fail generically either way.
        if now > expires or pending.attempts >= MAX_VERIFICATION_ATTEMPTS:
            session.delete(pending)
            session.commit()
            raise InvalidVerificationError()

        try:
            _ph.verify(pending.code_hash, code)
        except exceptions.VerifyMismatchError:
            pending.attempts += 1
            if pending.attempts >= MAX_VERIFICATION_ATTEMPTS:
                session.delete(pending)          #! last allowed guess used up — burn it
            session.commit()
            raise InvalidVerificationError()
        except (exceptions.InvalidHashError, exceptions.VerificationError):
            raise HTTPException(status_code=500, detail="Internal verification error")

        #* Code is correct. Re-check uniqueness (someone may have claimed the
        #* email/username since step 1), then create the account and consume the
        #* pending row in the same transaction.
        if session.scalar(select(User).where(User.email_bidx == email_bidx)):
            session.delete(pending)
            session.commit()
            raise ExistingUserError("email")
        if session.scalar(select(User).where(User.username == pending.username)):
            session.delete(pending)
            session.commit()
            raise ExistingUserError("username")

        user = User(
            email=email,                     # encrypted at rest by the column type; re-supplied by the client
            email_bidx=email_bidx,
            username=pending.username,
            password=pending.password_hash,  # already Argon2-hashed at request time
            role=ROLE_STUDENT,               # self-service signup can NEVER pick its own role
        )
        session.add(user)
        session.delete(pending)
        try:
            session.commit()
            session.refresh(user)
        except IntegrityError:
            raise ExistingUserError("username")

        token = create_access_token(user.user_id.hex, user.role)
        return token, user.user_id, user.role


async def resend_registration_code(email: EmailStr) -> Optional[Tuple[str, str, str]]:
    """Re-issue a fresh code for an in-flight signup, subject to a cooldown that
    stops the endpoint being used to flood someone's inbox.

    Returns ``(email, username, code)`` when a new code was issued, or ``None``
    (no pending signup, or still within the cooldown) — the caller returns an
    identical generic response either way so nothing leaks about pending signups."""
    email = email.strip().lower()
    email_bidx = blind_index(email)
    now = datetime.now(timezone.utc)

    with get_db_session() as session:
        pending = session.scalar(
            select(PendingRegistration).where(PendingRegistration.email_bidx == email_bidx)
        )
        if pending is None:
            return None

        last_sent = pending.last_sent_at
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)
        if (now - last_sent).total_seconds() < VERIFICATION_RESEND_COOLDOWN_SECONDS:
            return None                          #! within cooldown — don't send another email

        code = generate_verification_code()
        pending.code_hash = hash_password(code)
        pending.code_expires = now + timedelta(minutes=VERIFICATION_CODE_EXPIRE_MINUTES)
        pending.attempts = 0                     # fresh code resets the guess counter
        pending.last_sent_at = now
        username = pending.username
        session.commit()

    return email, username, code


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
        username = existing_user.username
        pwd_hash = existing_user.password


    if must_reset:
        #! A forced reset takes precedence over the OTP: the user must set a new
        #! password (via the reset token) before any session — no second factor here.
        raise PasswordResetRequiredError(create_reset_token(uid.hex, pwd_hash))

    #! Password OK, but authentication is NOT complete: stage a login challenge and
    #! demand the emailed 6-digit code. No session token is issued until it is
    #! confirmed (see verify_login_otp). The code is returned only so the caller can
    #! email it out of band — it is never sent to the client.
    code = _issue_login_challenge(uid)
    raise LoginOtpRequiredError(email=email, username=username, code=code)


def _issue_login_challenge(user_id: UUID) -> str:
    """Create (or replace) the pending login challenge for a user and return a
    fresh 6-digit code. Only the Argon2 hash of the code is stored. One challenge
    per user: a new login attempt overwrites any previous outstanding one."""
    code = generate_verification_code()
    now = datetime.now(timezone.utc)
    with get_db_session() as session:
        existing = session.scalar(
            select(LoginChallenge).where(LoginChallenge.user_id == user_id)
        )
        if existing:
            session.delete(existing)
            session.flush()
        session.add(LoginChallenge(
            user_id=user_id,
            code_hash=hash_password(code),
            code_expires=now + timedelta(minutes=LOGIN_OTP_EXPIRE_MINUTES),
            attempts=0,
            last_sent_at=now,
        ))
    return code


async def verify_login_otp(email: EmailStr, code: str) -> Tuple[str, UUID, str]:
    """Second step of login: confirm the emailed code and, only if it matches,
    issue the real session token. The code is single-use, time-limited, and capped
    at MAX_LOGIN_OTP_ATTEMPTS guesses.

    Returns ``(access_token, user_id, role)`` on success. Raises
    InvalidLoginOtpError for any bad/expired/exhausted/unknown code (one generic
    failure — no enumeration oracle)."""
    email = email.strip().lower()
    email_bidx = blind_index(email)

    with get_db_session() as session:
        user = session.scalar(select(User).where(User.email_bidx == email_bidx))
        challenge = (
            session.scalar(select(LoginChallenge).where(LoginChallenge.user_id == user.user_id))
            if user else None
        )

        #! No such user, no outstanding challenge, or the account is no longer
        #! eligible: burn the same Argon2 time as a real check so all these cases
        #! are indistinguishable by timing, then fail generically.
        if user is None or challenge is None or user.is_deleted or not user.is_active:
            try:
                _ph.verify(_DUMMY_HASH, code)
            except Exception:  # nosec B110
                pass
            raise InvalidLoginOtpError()

        now = datetime.now(timezone.utc)
        expires = challenge.code_expires
        if expires.tzinfo is None:               # tolerate a naive value from the DB driver
            expires = expires.replace(tzinfo=timezone.utc)

        #! Expired or out of guesses: burn the challenge — a fresh login is needed.
        if now > expires or challenge.attempts >= MAX_LOGIN_OTP_ATTEMPTS:
            session.delete(challenge)
            raise InvalidLoginOtpError()

        try:
            _ph.verify(challenge.code_hash, code)
        except exceptions.VerifyMismatchError:
            challenge.attempts += 1
            if challenge.attempts >= MAX_LOGIN_OTP_ATTEMPTS:
                session.delete(challenge)        #! last allowed guess used up — burn it
            raise InvalidLoginOtpError()
        except (exceptions.InvalidHashError, exceptions.VerificationError):
            raise HTTPException(status_code=500, detail="Internal authentication error")

        #* Code is correct: consume the challenge and issue a real session.
        uid = user.user_id
        role = user.role
        session.delete(challenge)

    return create_access_token(uid.hex, role), uid, role


async def resend_login_otp(email: EmailStr) -> Optional[Tuple[str, str, str]]:
    """Re-issue a fresh login code for an in-flight challenge, subject to a
    cooldown that stops the endpoint being used to flood someone's inbox.

    Returns ``(email, username, code)`` when a new code was issued, or ``None``
    (no outstanding challenge, ineligible account, or still within the cooldown) —
    the caller returns an identical generic response either way."""
    email = email.strip().lower()
    email_bidx = blind_index(email)
    now = datetime.now(timezone.utc)

    with get_db_session() as session:
        user = session.scalar(select(User).where(User.email_bidx == email_bidx))
        if not user or user.is_deleted or not user.is_active:
            return None
        challenge = session.scalar(
            select(LoginChallenge).where(LoginChallenge.user_id == user.user_id)
        )
        if challenge is None:
            return None

        last_sent = challenge.last_sent_at
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)
        if (now - last_sent).total_seconds() < LOGIN_OTP_RESEND_COOLDOWN_SECONDS:
            return None                          #! within cooldown — don't send another email

        code = generate_verification_code()
        challenge.code_hash = hash_password(code)
        challenge.code_expires = now + timedelta(minutes=LOGIN_OTP_EXPIRE_MINUTES)
        challenge.attempts = 0                   # fresh code resets the guess counter
        challenge.last_sent_at = now
        username = user.username

    return email, username, code


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
