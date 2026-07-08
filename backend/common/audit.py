from typing import Optional
from uuid import UUID

from model.models import AuditLog


def log_action(
    session,
    *,
    user_id: Optional[UUID],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[UUID] = None,
    outcome: str = "success",
    ip_address: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Append-only audit trail entry (SR-11). Uses the caller's session/transaction
    so the log write commits atomically with the action it records."""
    session.add(
        AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            ip_address=ip_address,
            details=details,
        )
    )
