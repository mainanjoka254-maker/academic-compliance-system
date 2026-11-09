from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles, is_super_admin, ensure_institution_access
from app.models.notification import AuditLog
from app.models.user import User
from app.models.role import Role
from app.models.institution import Institution
from app.models.student import Lecturer, Student
from app.services.audit_service import log_action
from app.services.notification_service import create_notification
from app.services.email_service import send_email

router = APIRouter(prefix="/admin", tags=["Administration"])

APPROVABLE_ROLES = {"lecturer", "registrar", "compliance_officer", "university_admin"}


class DecisionPayload(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)


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


@router.get("/account-requests")
def list_account_requests(
    institution_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("university_admin", "registrar", "super_admin")),
):
    q = db.query(User).filter(User.approval_status == "pending", User.requested_role.in_(APPROVABLE_ROLES))
    if is_super_admin(current_user):
        if institution_id is not None:
            q = q.filter(User.institution_id == institution_id)
    else:
        if current_user.institution_id is None:
            raise HTTPException(status_code=403, detail="An institution is required")
        q = q.filter(User.institution_id == current_user.institution_id)
    return [
        {
            "user_id": u.id, "email": u.email, "full_name": u.full_name, "phone": u.phone,
            "requested_role": u.requested_role, "staff_number": u.requested_staff_number,
            "institution_id": u.institution_id, "is_verified": u.is_verified, "created_at": str(u.created_at),
        }
        for u in q.order_by(User.created_at).all()
    ]


def _get_role(db: Session, name: str) -> Role:
    r = db.query(Role).filter(Role.name == name).first()
    if not r:
        r = Role(name=name, description=name, is_system=True)
        db.add(r); db.flush()
    return r


@router.post("/account-requests/{user_id}/approve")
def approve_account_request(
    user_id: int,
    request: Request,
    payload: DecisionPayload | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("university_admin", "super_admin")),
):
    user = db.query(User).filter(User.id == user_id, User.approval_status == "pending").first()
    if not user or user.requested_role not in APPROVABLE_ROLES:
        raise HTTPException(status_code=404, detail="Pending account request not found")
    if not is_super_admin(current_user):
        ensure_institution_access(current_user, user.institution_id)
    if not user.is_verified:
        raise HTTPException(status_code=409, detail="Applicant must verify email before approval")
    # Only super_admin may approve university_admin
    if user.requested_role == "university_admin" and not is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Only a platform administrator can approve university administrators")

    role = _get_role(db, user.requested_role)
    if role not in user.roles:
        user.roles.append(role)

    if user.requested_role == "lecturer" and user.requested_staff_number:
        if not db.query(Lecturer).filter(Lecturer.user_id == user.id).first():
            if db.query(Lecturer.id).filter(Lecturer.institution_id == user.institution_id, Lecturer.staff_number == user.requested_staff_number).first():
                raise HTTPException(status_code=409, detail="Staff number already assigned")
            db.add(Lecturer(institution_id=user.institution_id, user_id=user.id, staff_number=user.requested_staff_number, department_id=user.department_id))
    user.approval_status = "approved"
    user.is_active = True
    approved_role = user.requested_role
    user.requested_role = None
    reason = (payload.reason.strip() if payload and payload.reason else None) or None
    db.commit()
    approved_msg = f"Your {approved_role.replace('_',' ')} account has been approved. You can now sign in."
    if reason:
        approved_msg += f" Note: {reason}"
    create_notification(db, user.id, "Account approved", approved_msg, type_="account_approval", institution_id=user.institution_id)
    send_email(user.email, "ADCS account approved", approved_msg)
    log_action(db, "account_request.approved", user_id=current_user.id, institution_id=user.institution_id, resource_type="user", resource_id=user.id, ip_address=request.client.host if request.client else None, details=f"role={approved_role};reason={reason or ''}")
    return {"user_id": user.id, "approved_role": approved_role, "status": "approved", "reason": reason}


@router.post("/account-requests/{user_id}/reject")
def reject_account_request(
    user_id: int,
    request: Request,
    payload: DecisionPayload | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("university_admin", "registrar", "super_admin")),
):
    user = db.query(User).filter(User.id == user_id, User.approval_status == "pending").first()
    if not user or user.requested_role not in APPROVABLE_ROLES:
        raise HTTPException(status_code=404, detail="Pending account request not found")
    if not is_super_admin(current_user):
        ensure_institution_access(current_user, user.institution_id)
    # Registrar may not reject university_admin requests
    actor_roles = {r.name for r in current_user.roles}
    if user.requested_role == "university_admin" and not (is_super_admin(current_user) or "university_admin" in actor_roles):
        raise HTTPException(status_code=403, detail="Insufficient permissions to decide this request")
    reason = (payload.reason.strip() if payload and payload.reason else None) or None
    user.approval_status = "rejected"
    user.is_active = False
    db.commit()
    rejected_msg = "Your account request was not approved. Contact your institution for details."
    if reason:
        rejected_msg += f" Reason: {reason}"
    create_notification(db, user.id, "Account request not approved", rejected_msg, type_="account_approval", institution_id=user.institution_id)
    send_email(user.email, "ADCS account request update", rejected_msg)
    log_action(db, "account_request.rejected", user_id=current_user.id, institution_id=user.institution_id, resource_type="user", resource_id=user.id, ip_address=request.client.host if request.client else None, details=f"reason={reason or ''}")
    return {"user_id": user.id, "status": "rejected", "reason": reason}
