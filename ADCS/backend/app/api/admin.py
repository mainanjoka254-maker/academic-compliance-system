from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.deps import require_roles
from fastapi import HTTPException
from app.models.notification import AuditLog

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/audit-logs")
def audit_logs(db: Session = Depends(get_db), current_user=Depends(require_roles("super_admin", "university_admin", "compliance_officer"))):
    q = db.query(AuditLog)
    if not (current_user.is_superuser or any(r.name == "super_admin" for r in current_user.roles)):
        if current_user.institution_id is None:
            raise HTTPException(status_code=403, detail="An institution is required")
        q = q.filter(AuditLog.institution_id == current_user.institution_id)
    return [{"id": a.id, "user_id": a.user_id, "action": a.action, "resource_type": a.resource_type,
             "resource_id": a.resource_id, "ip_address": a.ip_address, "success": a.success,
             "details": a.details, "created_at": str(a.created_at)} for a in q.order_by(AuditLog.created_at.desc()).limit(200).all()]
