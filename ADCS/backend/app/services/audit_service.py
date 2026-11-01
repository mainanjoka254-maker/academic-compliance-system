from sqlalchemy.orm import Session
from typing import Optional

from app.models.notification import AuditLog


def log_action(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    institution_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    details: Optional[str] = None,
    success: bool = True,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        institution_id=institution_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        details=details,
        success=success,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
