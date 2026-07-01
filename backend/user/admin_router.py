from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, func

from core.rate_limit import limiter
from common.audit import log_action
from common.security import to_uuid, parse_uid as _parse_uid, client_ip as _client_ip
from common.encryption import blind_index
from db.db import get_db_session
from model.models import User
from .auth import (
    hash_password, generate_temp_password, validate_password_strength,
    ALLOWED_ROLES, ROLE_ADMIN, ROLE_STUDENT, PasswordPolicyError,
)
from .auth_router import require_admin

router = APIRouter(prefix="/api/v1/admin", tags=["Admin - User Management"])


class AdminUserView(BaseModel):
    user_id: str
    username: str
    email: EmailStr
    role: str
    is_active: bool
    is_deleted: bool
    force_password_reset: bool
    auth_attempts: int


class CreateUserRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=150)
    role: str = Field(default=ROLE_STUDENT)


class AssignRoleRequest(BaseModel):
    role: str


class SetStatusRequest(BaseModel):
    is_active: bool

class TempPasswordResponse(BaseModel):
    user_id: str
    temp_password: str
    detail: str = "Share this one-time password over a secure channel. The user must change it on next login."


# --- Helpers ---
def _to_view(user: User) -> AdminUserView:
    return AdminUserView(
        user_id=user.user_id.hex,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        is_deleted=user.is_deleted,
        force_password_reset=user.force_password_reset,
        auth_attempts=user.auth_attempts,
    )


def parse_uuid(raw: str) -> UUID:
    #* Shared UUID parser, just with this router's "user id" wording on failure.
    return to_uuid(raw, detail="Invalid user id")


def retrieve_user(session, uid: UUID) -> User:
    user = session.scalar(select(User).where(User.user_id == uid))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def validate_role(role: str) -> str:
    role = (role or "").strip().lower()
    if role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Allowed: {', '.join(sorted(ALLOWED_ROLES))}",
        )
    return role

#? Counts live admins (optionally excluding one) — used to block demoting/banning the last admin.
def _count_active_admins(session, exclude_id: Optional[UUID] = None) -> int:
    stmt = select(func.count()).select_from(User).where(
        User.role == ROLE_ADMIN,
        User.is_active.is_(True),
        User.is_deleted.is_(False),
    )
    if exclude_id is not None:
        stmt = stmt.where(User.user_id != exclude_id)
    return session.scalar(stmt) or 0


# --- Endpoints ---
@router.get("/users", response_model=List[AdminUserView])
async def list_users(
    request: Request,
    include_deleted: bool = False,
    admin: dict = Depends(require_admin),
):
    with get_db_session() as session:
        stmt = select(User).order_by(User.username)
        if not include_deleted:
            stmt = stmt.where(User.is_deleted.is_(False))
        users = session.scalars(stmt).all()
        return [_to_view(u) for u in users]


@router.post("/users", response_model=TempPasswordResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")  # credential-issuing endpoint — cap even for a compromised admin token
async def create_user(request: Request, req: CreateUserRequest, admin: dict = Depends(require_admin)):

    role = validate_role(req.role)
    email = req.email.strip().lower()
    username = req.username.strip()

    temp_password = generate_temp_password()
    hashed = hash_password(temp_password)

    with get_db_session() as session:
        #? email is encrypted at rest, so dedupe by its blind index rather than the value.
        if session.scalar(select(User).where(User.email_bidx == blind_index(email))):
            raise HTTPException(status_code=409, detail="A user with that email already exists")
        if session.scalar(select(User).where(User.username == username)):
            raise HTTPException(status_code=409, detail="A user with that username already exists")

        user = User(
            email=email,
            email_bidx=blind_index(email),
            username=username,
            password=hashed,
            role=role,
            is_active=True,
            force_password_reset=True,  # must rotate the temp password on first login
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        uid_hex = user.user_id.hex

    return TempPasswordResponse(user_id=uid_hex, temp_password=temp_password)


@router.patch("/users/{user_id}/role", response_model=AdminUserView)
async def assign_role(request: Request, user_id: str, req: AssignRoleRequest, admin: dict = Depends(require_admin)):
    uid = parse_uuid(user_id)
    role = validate_role(req.role)

    with get_db_session() as session:
        user = retrieve_user(session, uid)

        #! Don't let an admin demote the last remaining admin (including themselves) — would lock everyone out of admin.
        if user.role == ROLE_ADMIN and role != ROLE_ADMIN:
            if _count_active_admins(session, exclude_id=uid) == 0:
                raise HTTPException(status_code=409, detail="Cannot demote the last remaining admin")

        user.role = role
        #! SR-11: a role change is security-relevant, so record it in the audit log.
        log_action(
            session, user_id=_parse_uid(admin), action="assign_role",
            resource_type="user", resource_id=uid, ip_address=_client_ip(request),
            details={"new_role": role},
        )
        session.commit()
        session.refresh(user)
        return _to_view(user)


@router.patch("/users/{user_id}/status", response_model=AdminUserView)
async def set_status(request: Request, user_id: str, req: SetStatusRequest, admin: dict = Depends(require_admin)):

    uid = parse_uuid(user_id)

    #! Cannot ban themselves
    if not req.is_active and admin["user_id"] == user_id:
        raise HTTPException(status_code=409, detail="You cannot ban your own account")

    with get_db_session() as session:
        user = retrieve_user(session, uid)

        #! Cannot ban admin accounts
        if not req.is_active and user.role == ROLE_ADMIN:
            raise HTTPException(status_code=409, detail="Cannot ban admin accounts")

        user.is_active = req.is_active
        if req.is_active:
            user.auth_attempts = 0  # unlock on (re)activation
        # SR-11: account suspension/reactivation is a security-relevant event.
        log_action(
            session, user_id=_parse_uid(admin),
            action="suspend_account" if not req.is_active else "reactivate_account",
            resource_type="user", resource_id=uid, ip_address=_client_ip(request),
            details={"is_active": req.is_active},
        )
        session.commit()
        session.refresh(user)
        return _to_view(user)


@router.post("/users/{user_id}/reset-password", response_model=TempPasswordResponse)
@limiter.limit("20/minute")  # credential-issuing endpoint — cap even for a compromised admin token
async def reset_password(request: Request, user_id: str, admin: dict = Depends(require_admin)):
    """Reset (not set) a user's password to a new strong random value.
    The admin never chooses the value; it is returned once for secure handoff."""
    uid = parse_uuid(user_id)
    temp_password = generate_temp_password()

    # Defensive: ensure the generated value satisfies our own policy.
    try:
        validate_password_strength(temp_password)
    except PasswordPolicyError:
        temp_password = generate_temp_password(24)

    hashed = hash_password(temp_password)

    with get_db_session() as session:
        user = retrieve_user(session, uid)
        user.password = hashed
        user.force_password_reset = True
        user.auth_attempts = 0  # clear any lockout so the user can sign in with the temp password
        session.commit()
        uid_hex = user.user_id.hex

    return TempPasswordResponse(user_id=uid_hex, temp_password=temp_password)
