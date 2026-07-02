from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from db.db import get_db_session
from model.models import User
from model.response_model import ResponseModel
from .auth import (
    register, login, change_password, decode_access_token, parse_user_id,
    ExistingUserError, UserNotFoundError, PasswordsMismatchError,
    AccountLockedError, InactiveAccountError, DatabaseError, PasswordPolicyError,
    PasswordResetRequiredError, MIN_PASSWORD_LENGTH, ROLE_INSTRUCTOR, ROLE_ADMIN, SCOPE_PASSWORD_RESET,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# --- JWT dependency ---
async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # A password-reset token authorises ONLY /change-password — never a session.
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
    with get_db_session() as session:
            user = session.scalar(select(User).where(User.user_id == current_user["user_id"]))

            # Defense in depth
            if not user.is_active or user.is_deleted or user.role != "admin":
                raise HTTPException(status_code=401, detail="Invalid Credentials or Banned Account")
    return current_user


async def require_instructor(current_user: dict = Depends(get_current_user)) -> dict:
    """Deny-by-default gate for course-authoring endpoints (SR-03). Admins are
    also allowed through so staff can manage any course if needed."""
    if current_user["role"] not in (ROLE_INSTRUCTOR, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Instructor access required")
    return current_user


async def get_reset_subject(token: str = Depends(oauth2_scheme)) -> str:

    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired reset token")
    if payload.get("scope") != SCOPE_PASSWORD_RESET:
        raise HTTPException(status_code=403, detail="A password-reset token is required here")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid reset token")
    return sub

# --- Request/Response Schemas ---
class UserRegistrationSchema(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=150)
    password: str = Field(
        ...,
        min_length=MIN_PASSWORD_LENGTH,
        max_length=128,
        description="Min length 12, with upper/lower/digit/special. Full policy enforced server-side.",
    )
    password_confirm: str

class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str

class AuthResponseSchema(ResponseModel):
    access_token: str
    user_id: str
    user_role: str
    token_type: str = "bearer"

class UserProfileResponse(BaseModel):
    username: str
    email: EmailStr
    role: str

class ChangePasswordSchema(BaseModel):
    new_password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=128)
    new_password_confirm: str


# --- Endpoints ---
@router.post("/register", response_model=AuthResponseSchema, status_code=status.HTTP_201_CREATED)
async def register_user(request: Request, req: UserRegistrationSchema):
    try:
        access_token, user_id, role = await register(
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

    return AuthResponseSchema(access_token=access_token, user_id=user_id.hex, user_role=role)


@router.post("/login", response_model=AuthResponseSchema)
async def login_user(request: Request, req: UserLoginSchema):
    try:
        access_token, user_id, role = await login(req.email, req.password)
    except PasswordResetRequiredError as e:

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "force_password_reset": True, # nosec B105
                "reset_token": e.reset_token,
                "token_type": "reset", # nosec B105
            },
        )
    except AccountLockedError:
        raise HTTPException(
            status_code=423,
            detail="Account locked after too many failed attempts. Contact support to unlock.",
        )
    except InactiveAccountError:
        # Banned/deleted accounts: do not hint that the credentials were correct.
        raise HTTPException(status_code=403, detail="This account is not allowed to sign in")
    except (UserNotFoundError, PasswordsMismatchError):
        # Generic message — do not reveal whether email exists
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    return AuthResponseSchema(access_token=access_token, user_id=user_id.hex, user_role=role)


@router.get("/getProfile", response_model=UserProfileResponse)
async def get_profile(request: Request, current_user: dict = Depends(get_current_user)):
    try:
        uid = parse_user_id(current_user["user_id"])
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token subject")


    with get_db_session() as session:
        user = session.scalar(select(User).where(User.user_id == uid))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserProfileResponse(username=user.username, email=user.email, role=user.role)


@router.post("/change-password", response_model=AuthResponseSchema)
async def change_password_route(
    request: Request,
    req: ChangePasswordSchema,
    sub: str = Depends(get_reset_subject),
):

    try:
        uid = parse_user_id(sub)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid reset token subject")

    try:
        access_token, user_id, role = await change_password(
            uid, req.new_password, req.new_password_confirm
        )
    except PasswordsMismatchError:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    except PasswordPolicyError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")

    return AuthResponseSchema(access_token=access_token, user_id=user_id.hex, user_role=role)
