"""Shared request/identity helpers.

These tiny input-validation utilities were previously copied into nearly every
router. Centralising them keeps the behaviour identical in one place:
  * pull the authenticated user id out of the JWT claims,
  * parse an untrusted path parameter into a UUID,
  * read the client IP for audit logging.
"""
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, Request


def parse_uid(current_user: dict) -> UUID:
    """Return the authenticated user's id as a UUID, or 401 if the token's
    subject is missing or malformed."""
    try:
        return UUID(current_user["user_id"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token subject")


def to_uuid(raw: str, *, detail: str = "Invalid resource id") -> UUID:
    """Parse an untrusted string (e.g. a path parameter) into a UUID, raising a
    400 with the given message on failure."""
    try:
        return UUID(raw)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=detail)


def client_ip(request: Request) -> Optional[str]:
    """Best-effort client IP for audit records."""
    return request.client.host if request.client else None
