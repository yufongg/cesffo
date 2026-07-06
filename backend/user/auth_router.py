import os
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from core.rate_limit import limiter
from core.securedCookie import oauth2_scheme, set_auth_cookie, clear_auth_cookie
from common.audit import log_action
from common.email import (
    send_password_reset_email, send_verification_code_email, send_login_code_email,
)
from common.security import client_ip as _client_ip, parse_uid as _parse_uid
from db.db import get_db_session
from model.models import User
from model.response_model import ResponseModel
from .auth import (
    request_registration, verify_registration, resend_registration_code,
    login, verify_login_otp, resend_login_otp,
    change_password, change_password_authenticated, update_profile,
    request_password_reset, decode_access_token,
    ExistingUserError, UserNotFoundError, PasswordsMismatchError,
    AccountLockedError, InactiveAccountError, DatabaseError, PasswordPolicyError,
    PasswordResetRequiredError, InvalidCurrentPasswordError, ResetTokenInvalidError,
    InvalidVerificationError, LoginOtpRequiredError, InvalidLoginOtpError,
    MIN_PASSWORD_LENGTH, RESET_LINK_EXPIRE_MINUTES, VERIFICATION_CODE_EXPIRE_MINUTES,
    LOGIN_OTP_EXPIRE_MINUTES,
    ROLE_ADMIN, ROLE_INSTRUCTOR,
    USERNAME_MIN_LENGTH, USERNAME_MAX_LENGTH, SCOPE_PASSWORD_RESET, AUTH_SUCCESS
)


router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")

# Returned identically whether or not the email exists — anti-enumeration.
_GENERIC_RESET_MESSAGE = (
    "If an account exists for that email, a password reset link has been sent."
)

# Returned by /register and /register/resend regardless of whether the details
# are valid or a signup is pending — keeps both from leaking which emails exist.
_GENERIC_VERIFICATION_MESSAGE = (
    "If those details are valid, a 6-digit verification code has been sent to your email."
)

# Returned by /login (on correct password) and /login/resend regardless of whether
# the account exists — the OTP email only actually goes out for a real, eligible
# account, but the response is identical so neither leaks which emails are registered.
_GENERIC_LOGIN_OTP_MESSAGE = (
    "If those credentials are valid, a 6-digit sign-in code has been sent to your email."
)

reset_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class LoginResponse(BaseModel):
    user_role: str
    user_id: str

# --- JWT dependency ---
async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    #! A password-reset token authorises ONLY /change-password — it must never unlock a normal session.
    if payload.get("scope") == SCOPE_PASSWORD_RESET:
        raise HTTPException(status_code=401, detail="Password reset required before continuing")

    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid Credentials or Banned Account")

    with get_db_session() as session:
        user = session.scalar(select(User).where(User.user_id == user_id))
        if user is None or not user.is_active or user.is_deleted:
            raise HTTPException(status_code=401, detail="Invalid Credentials or Banned Account")

        role = user.role

    return {"user_id": user_id, "role": role}


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def require_instructor(current_user: dict = Depends(get_current_user)) -> dict:
    """Deny-by-default gate for course-authoring endpoints (SR-03). Admins are
    also allowed through so staff can manage any course if needed."""
    if current_user["role"] not in (ROLE_INSTRUCTOR, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Instructor access required")
    return current_user


async def get_reset_token_claims(token: str = Depends(reset_scheme)) -> dict:
    """Validate a password-reset bearer token and return its claims (subject +
    single-use fingerprint). Rejects anything that is not a reset-scoped token."""
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired reset token")
    if payload.get("scope") != SCOPE_PASSWORD_RESET:
        raise HTTPException(status_code=403, detail="A password-reset token is required here")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid reset token")
    return {"sub": sub, "pfp": payload.get("pfp")}

# --- Request/Response Schemas ---
class UserRegistrationSchema(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=150)
    password: str = Field(
        ...,
        min_length=MIN_PASSWORD_LENGTH,
        max_length=128,
        description="Min 8 chars with an uppercase, lowercase, number and special character. Full policy enforced server-side.",
    )
    password_confirm: str

class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str

class AuthResponseSchema(ResponseModel):
    detail: str

class UserProfileResponse(BaseModel):
    username: str
    email: EmailStr
    role: str

class ChangePasswordSchema(BaseModel):
    new_password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=128)
    new_password_confirm: str


class ForgotPasswordSchema(BaseModel):
    email: EmailStr


class VerifyRegistrationSchema(BaseModel):
    email: EmailStr
    code: str = Field(..., pattern=r"^\d{6}$", description="The 6-digit code emailed at registration.")


class ResendCodeSchema(BaseModel):
    email: EmailStr


class VerifyLoginOtpSchema(BaseModel):
    email: EmailStr
    code: str = Field(..., pattern=r"^\d{6}$", description="The 6-digit code emailed after the password step.")


class ResendLoginOtpSchema(BaseModel):
    email: EmailStr


class UpdateProfileSchema(BaseModel):
    # Both optional (change either or both); the "at least one" rule is enforced in the route.
    username: str | None = Field(
        default=None, min_length=USERNAME_MIN_LENGTH, max_length=USERNAME_MAX_LENGTH
    )
    email: EmailStr | None = None


class ChangeMyPasswordSchema(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=128)
    new_password_confirm: str


# --- Registration audit (SR-11) ---
def _record_registration_event(*, action, user_id, ip, outcome="success"):
    #! Append registration events to the append-only audit log in their own
    #! transaction. NEVER logs the email or the code — only action / outcome / IP.
    with get_db_session() as session:
        log_action(session, user_id=user_id, action=action, outcome=outcome, ip_address=ip)


# --- Endpoints ---
@router.post("/register", response_model=AuthResponseSchema)
@limiter.limit("5/minute")  # throttle automated account creation / verification-email spam
async def register_user(
    request: Request,
    req: UserRegistrationSchema,
    background_tasks: BackgroundTasks,
):
    """Step 1 of signup. Validates the details and emails a 6-digit code; the
    account is NOT created and the user is NOT logged in until the code is
    confirmed at /register/verify."""
    ip = _client_ip(request)
    try:
        email, username, code = await request_registration(
            req.email, req.username, req.password, req.password_confirm
        )
    except PasswordsMismatchError:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    except PasswordPolicyError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except ExistingUserError as e:
        raise HTTPException(status_code=409, detail=f"There is an existing user with the same {e.field_taken}")
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Registration failed due to a server error")

    #! Send the code AFTER the response so SMTP latency/errors stay off the request path.
    background_tasks.add_task(
        send_verification_code_email, email, username, code, VERIFICATION_CODE_EXPIRE_MINUTES
    )
    background_tasks.add_task(
        _record_registration_event, action="register_request", user_id=None, ip=ip, outcome="success"
    )
    return AuthResponseSchema(detail=_GENERIC_VERIFICATION_MESSAGE)


@router.post("/register/verify", response_model=LoginResponse)
@limiter.limit("10/minute")  # blunt online guessing of the 6-digit code per IP
async def verify_registration_route(
    request: Request,
    req: VerifyRegistrationSchema,
    response: Response,
    background_tasks: BackgroundTasks,
):
    """Step 2 of signup. Confirms the emailed code; on success the account is
    created and a session cookie is issued (auto-login)."""
    ip = _client_ip(request)
    try:
        access_token, user_id, role = await verify_registration(req.email, req.code)
    except InvalidVerificationError:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    except ExistingUserError as e:
        raise HTTPException(status_code=409, detail=f"There is an existing user with the same {e.field_taken}")
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Registration failed due to a server error")

    background_tasks.add_task(
        _record_registration_event, action="register_verify", user_id=user_id, ip=ip, outcome="success"
    )
    # Verification succeeded: establish a real session, same as login.
    set_auth_cookie(response, access_token)
    return LoginResponse(user_role=role, user_id=user_id.hex)


@router.post("/register/resend", response_model=AuthResponseSchema)
@limiter.limit("3/minute")  # tight cap: this endpoint triggers outbound email
async def resend_registration_code_route(
    request: Request,
    req: ResendCodeSchema,
    background_tasks: BackgroundTasks,
):
    """Re-send the verification code for an in-flight signup. Always returns the
    same generic message (and is cooldown-limited server-side), so it reveals
    nothing about which signups are pending."""
    try:
        result = await resend_registration_code(req.email)
    except Exception:
        result = None
    if result:
        email, username, code = result
        background_tasks.add_task(
            send_verification_code_email, email, username, code, VERIFICATION_CODE_EXPIRE_MINUTES
        )
    return AuthResponseSchema(detail=_GENERIC_VERIFICATION_MESSAGE)


def _record_login_attempt(*, user_id, outcome, ip, reason=None):
    #! SR-11: write the login attempt to the append-only audit log in ITS OWN
    #! transaction, so the record survives even if the request later errors out.
    #! The attempted email is deliberately never logged (keeps PII out of logs and
    #! avoids an enumeration oracle); attempts with no resolved account get a null user.
    details = {"reason": reason} if reason else None
    with get_db_session() as session:
        log_action(
            session, user_id=user_id, action="login",
            outcome=outcome, ip_address=ip, details=details,
        )


def _record_password_reset_request(*, user_id, ip):
    """SR-11: persist a self-service reset request to the append-only audit log in
    its own transaction (mirrors _record_login_attempt)."""
    with get_db_session() as session:
        log_action(
            session, user_id=user_id, action="password_reset_request",
            outcome="success", ip_address=ip,
        )


@router.post("/login")
@limiter.limit("10/minute")  # blunt brute-force / credential-stuffing per IP (lockout guards per-account)
async def login_user(
    request: Request,
    req: UserLoginSchema,
    background_tasks: BackgroundTasks,
):
    """Step 1 of login. Verifies the password only — it does NOT establish a
    session. On success a 6-digit code is emailed and the client must confirm it
    at /login/verify (login 2FA). The forced-password-reset path is unchanged and
    still takes precedence over the second factor."""
    ip = _client_ip(request)
    try:
        await login(req.email, req.password)
    except LoginOtpRequiredError as e:
        # Password was correct: the account owes a second factor now. Record the
        # password step as a success and email the code AFTER responding so SMTP
        # latency/errors stay off the request path.
        _record_login_attempt(user_id=None, outcome="success", ip=ip, reason="otp_sent")
        background_tasks.add_task(
            send_login_code_email, e.email, e.username, e.code, LOGIN_OTP_EXPIRE_MINUTES
        )
        # otp_required is a flow flag, not a credential (bandit B105).
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"otp_required": True, "detail": _GENERIC_LOGIN_OTP_MESSAGE},  # nosec B105
        )
    except PasswordResetRequiredError as e:
        # Credentials were correct but a forced reset is pending — the auth itself
        # succeeded, so record it as a success (uid is not exposed on this path).
        _record_login_attempt(user_id=None, outcome="success", ip=ip, reason="reset_required")
        # Response labels/flags below are not credentials (bandit B105).
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "force_password_reset": True,  # nosec B105
                "reset_token": e.reset_token,
                "token_type": "reset",  # nosec B105
            },
        )
    except AccountLockedError:
        _record_login_attempt(user_id=None, outcome="failure", ip=ip, reason="account_locked")
        raise HTTPException(
            status_code=423,
            detail="Account locked after too many failed attempts. Contact support to unlock.",
        )
    except InactiveAccountError:
        _record_login_attempt(user_id=None, outcome="failure", ip=ip, reason="inactive_account")
        # Banned/deleted accounts: do not hint that the credentials were correct.
        raise HTTPException(status_code=403, detail="This account is not allowed to sign in")
    except (UserNotFoundError, PasswordsMismatchError):
        _record_login_attempt(user_id=None, outcome="failure", ip=ip, reason="bad_credentials")
        # Generic message — do not reveal whether email exists
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    # login() always resolves via one of the exceptions above; reaching here means
    # the second factor was skipped, which would be an auth bypass. Fail closed.
    raise HTTPException(status_code=500, detail="Authentication error")


@router.post("/login/verify", response_model=LoginResponse)
@limiter.limit("10/minute")  #! More stringent to prevent guessing of OTP
async def verify_login_route(
    request: Request,
    req: VerifyLoginOtpSchema,
    response: Response,
):
    """
    Confirms the emailed code; only on success is the session
    cookie issued. A wrong/expired/exhausted code fails generically.
    """
    
    ip = _client_ip(request)
    try:
        access_token, user_id, role = await verify_login_otp(req.email, req.code)
    except InvalidLoginOtpError:
        _record_login_attempt(user_id=None, outcome="failure", ip=ip, reason="bad_otp")
        raise HTTPException(status_code=401, detail="Invalid or expired sign-in code")

    _record_login_attempt(user_id=user_id, outcome="success", ip=ip)
    set_auth_cookie(response, access_token)
    return LoginResponse(user_role=role, user_id=user_id.hex)


@router.post("/login/resend", response_model=AuthResponseSchema)
@limiter.limit("3/minute")  # tight cap: this endpoint triggers outbound email
async def resend_login_otp_route(
    request: Request,
    req: ResendLoginOtpSchema,
    background_tasks: BackgroundTasks,
):
    """Re-send the sign-in code for an in-flight login challenge. Always returns
    the same generic message (and is cooldown-limited server-side), so it reveals
    nothing about which accounts have a challenge pending."""
    try:
        result = await resend_login_otp(req.email)
    except Exception:
        result = None
    if result:
        email, username, code = result
        background_tasks.add_task(
            send_login_code_email, email, username, code, LOGIN_OTP_EXPIRE_MINUTES
        )
    return AuthResponseSchema(detail=_GENERIC_LOGIN_OTP_MESSAGE)


@router.post("/logout", response_model=AuthResponseSchema)
async def logout(response: Response):
    # Only the server can clear an httpOnly cookie; match the set attributes so
    # the browser actually drops it.
    clear_auth_cookie(response)
    return AuthResponseSchema(detail = AUTH_SUCCESS)

@router.get("/getProfile", response_model=UserProfileResponse)
async def get_profile(request: Request, current_user: dict = Depends(get_current_user)):
    uid = _parse_uid(current_user)
    with get_db_session() as session:
        user = session.scalar(select(User).where(User.user_id == uid))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserProfileResponse(username=user.username, email=user.email, role=user.role)


@router.patch("/profile", response_model=UserProfileResponse)
@limiter.limit("10/minute")  # limit profile churn / username-enumeration probing
async def update_profile_route(
    request: Request,
    req: UpdateProfileSchema,
    current_user: dict = Depends(get_current_user),
):
    if req.username is None and req.email is None:
        raise HTTPException(status_code=400, detail="Provide a username and/or email to update")

    uid = _parse_uid(current_user)
    try:
        username, email, role = await update_profile(
            uid, username=req.username, email=req.email
        )
    except PasswordPolicyError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except ExistingUserError as e:
        raise HTTPException(status_code=409, detail=f"There is an existing user with the same {e.field_taken}")
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Profile update failed due to a server error")

    return UserProfileResponse(username=username, email=email, role=role)


@router.post("/change-my-password", response_model=AuthResponseSchema)
@limiter.limit("5/minute")  # limit online password-guessing of the current password
async def change_my_password_route(
    request: Request,
    req: ChangeMyPasswordSchema,
    current_user: dict = Depends(get_current_user),
):
    """Self-service password change for a logged-in user. Requires the current
    password (verified server-side) — distinct from /change-password, which is
    the forced-reset flow gated by a one-time reset token."""
    uid = _parse_uid(current_user)
    try:
        await change_password_authenticated(
            uid, req.current_password, req.new_password, req.new_password_confirm
        )
    except InvalidCurrentPasswordError:
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    except PasswordsMismatchError:
        raise HTTPException(status_code=400, detail="New passwords do not match")
    except PasswordPolicyError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")

    return AuthResponseSchema(detail=AUTH_SUCCESS)


@router.post("/forgot-password", response_model=AuthResponseSchema)
@limiter.limit("5/minute")  # throttle reset-email spam / enumeration probing per IP
async def forgot_password_route(
    request: Request,
    req: ForgotPasswordSchema,
    background_tasks: BackgroundTasks,
):
    """Self-service password reset: email a one-time link to the account owner.

    Always returns 200 with the same generic message whether or not the email
    exists, so it can't be used to discover which addresses are registered. The
    email is sent from a background task so the response time doesn't depend on
    account existence either (timing-oracle defence).
    """
    ip = _client_ip(request)
    try:
        result = await request_password_reset(req.email)
    except Exception:
        # Never let an internal error reveal whether the account exists.
        result = None

    if result:
        uid, token, username, email = result
        reset_link = f"{FRONTEND_BASE_URL.rstrip('/')}/reset-password?token={quote(token)}"
        #! Send after the response is returned — keeps response timing uniform and
        #! keeps SMTP latency/errors off the request path (timing-oracle defence).
        background_tasks.add_task(
            send_password_reset_email, email, username, reset_link, RESET_LINK_EXPIRE_MINUTES
        )
        #! SR-11: audit in the background too, so the request does identical work whether
        #! or not the account exists (otherwise the timing leaks which emails are registered).
        background_tasks.add_task(_record_password_reset_request, user_id=uid, ip=ip)

    return AuthResponseSchema(detail=_GENERIC_RESET_MESSAGE)


@router.post("/change-password", response_model=LoginResponse)
@limiter.limit("5/minute")  # limit reset-token replay / password-churn attempts
async def change_password_route(
    request: Request,
    req: ChangePasswordSchema,
    response: Response,
    claims: dict = Depends(get_reset_token_claims),
):

    try:
        uid = UUID(claims["sub"])
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid reset token subject")

    try:
        access_token, user_id, role = await change_password(
            uid, req.new_password, req.new_password_confirm,
            expected_fingerprint=claims.get("pfp"),
        )
    except ResetTokenInvalidError:
        raise HTTPException(
            status_code=401,
            detail="This reset link is no longer valid. Please request a new one.",
        )
    except PasswordsMismatchError:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    except PasswordPolicyError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")

    # A successful reset establishes a real session, so issue the cookie now.
    set_auth_cookie(response, access_token)
    return LoginResponse(user_role=role, user_id=user_id.hex)
