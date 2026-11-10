import hashlib
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user, hash_password, verify_password
from app.models.user import User
from app.models.user_profile import UserProfile, StudentProfile, LecturerProfile, StaffProfile
from app.models.student import Student, Lecturer
from app.models.institution import Institution
from app.models.department import Department
from app.models.notification import EmailVerificationToken
from app.models.session import UserSession, LoginHistory
from app.models.activity import UserActivityLog
from app.models.support_ticket import SupportTicket, SupportTicketMessage
from app.services.audit_service import log_action
from app.services.account_service import log_activity
from app.services.email_service import send_email
from app.services.notification_service import create_notification
from app.core.rate_limit import limiter

router = APIRouter(prefix="/profile", tags=["Profile"])

ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_IMAGE_BYTES = 3 * 1024 * 1024
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _roles(user: User):
    return [r.name for r in user.roles]


def _ensure_profiles(db: Session, user: User):
    if not db.query(UserProfile).filter(UserProfile.user_id == user.id).first():
        db.add(UserProfile(user_id=user.id))
    roles = set(_roles(user))
    if "student" in roles and not db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first():
        sp = db.query(Student).filter(Student.user_id == user.id).first()
        db.add(StudentProfile(user_id=user.id, student_id=sp.id if sp else None))
    if "lecturer" in roles and not db.query(LecturerProfile).filter(LecturerProfile.user_id == user.id).first():
        lp = db.query(Lecturer).filter(Lecturer.user_id == user.id).first()
        db.add(LecturerProfile(user_id=user.id, lecturer_id=lp.id if lp else None))
    staff_role = next((r for r in ["registrar", "compliance_officer", "university_admin", "super_admin"] if r in roles), None)
    if staff_role and not db.query(StaffProfile).filter(StaffProfile.user_id == user.id).first():
        db.add(StaffProfile(user_id=user.id, staff_role=staff_role, staff_number=getattr(user, "requested_staff_number", None)))
    db.flush()


def _institution_info(db: Session, user: User):
    if not user.institution_id:
        return None
    inst = db.query(Institution).filter(Institution.id == user.institution_id).first()
    if not inst:
        return None
    return {"id": inst.id, "name": inst.name, "code": inst.code, "type": inst.type, "email": inst.email, "phone": inst.phone, "address": inst.address, "country": inst.country}


def _student_data(db: Session, user: User):
    s = db.query(Student).filter(Student.user_id == user.id).first()
    if not s:
        return None
    dept = db.query(Department).filter(Department.id == s.department_id).first() if s.department_id else None
    sp = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
    return {
        "student_record_id": s.id,
        "student_number": s.student_number,
        "program": s.program,
        "year_of_study": s.year_of_study,
        "enrollment_date": s.enrollment_date,
        "status": s.status,
        "attendance_percentage": s.attendance_percentage,
        "gpa": s.gpa,
        "department": {"id": dept.id, "name": dept.name, "code": dept.code} if dept else None,
        "faculty": {"id": dept.faculty.id, "name": dept.faculty.name} if dept and getattr(dept, "faculty", None) else None,
        "profile": {
            "emergency_contact_name": getattr(sp, "emergency_contact_name", None),
            "emergency_contact_phone": getattr(sp, "emergency_contact_phone", None),
            "emergency_contact_relation": getattr(sp, "emergency_contact_relation", None),
            "admission_date": getattr(sp, "admission_date", None),
            "academic_status": getattr(sp, "academic_status", None) or s.status,
            "academic_progress_summary": getattr(sp, "academic_progress_summary", None),
            "compliance_status": getattr(sp, "compliance_status", None),
        } if sp else None,
    }


def _lecturer_data(db: Session, user: User):
    l = db.query(Lecturer).filter(Lecturer.user_id == user.id).first()
    if not l:
        return None
    dept = db.query(Department).filter(Department.id == l.department_id).first() if l.department_id else None
    lp = db.query(LecturerProfile).filter(LecturerProfile.user_id == user.id).first()
    return {
        "lecturer_record_id": l.id,
        "staff_number": l.staff_number,
        "title": l.title,
        "specialization": l.specialization,
        "department": {"id": dept.id, "name": dept.name, "code": dept.code} if dept else None,
        "faculty": {"id": dept.faculty.id, "name": dept.faculty.name} if dept and getattr(dept, "faculty", None) else None,
        "profile": {
            "professional_title": getattr(lp, "professional_title", None),
            "professional_details": getattr(lp, "professional_details", None),
            "office_location": getattr(lp, "office_location", None),
            "office_hours": getattr(lp, "office_hours", None),
        } if lp else None,
    }


def _staff_data(db: Session, user: User):
    sp = db.query(StaffProfile).filter(StaffProfile.user_id == user.id).first()
    if not sp:
        return None
    return {
        "staff_role": sp.staff_role,
        "staff_number": sp.staff_number,
        "job_title": sp.job_title,
        "office": sp.office,
        "responsibilities": sp.responsibilities,
    }


def _serialize_profile(db: Session, user: User):
    up = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    dept = db.query(Department).filter(Department.id == user.department_id).first() if user.department_id else None
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "gender": getattr(up, "gender", None),
        "date_of_birth": getattr(up, "date_of_birth", None),
        "address": getattr(up, "address", None),
        "biography": getattr(up, "biography", None),
        "profile_picture_path": getattr(up, "profile_picture_path", None),
        "account_created_at": user.created_at,
        "account_status": "active" if user.is_active else ("pending" if getattr(user, "approval_status", None) == "pending" else "inactive"),
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "approval_status": getattr(user, "approval_status", None),
        "institution_id": user.institution_id,
        "department_id": user.department_id,
        "department": {"id": dept.id, "name": dept.name, "code": dept.code} if dept else None,
        "institution": _institution_info(db, user),
        "roles": _roles(user),
        "last_login_at": user.last_login_at,
        "student": _student_data(db, user),
        "lecturer": _lecturer_data(db, user),
        "staff": _staff_data(db, user),
    }


@router.get("/me")
def get_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _ensure_profiles(db, current_user)
    db.commit()
    db.refresh(current_user)
    return _serialize_profile(db, current_user)


@router.patch("/me")
def update_profile(payload: dict, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _ensure_profiles(db, current_user)
    up = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    roles = set(_roles(current_user))

    if "full_name" in payload and isinstance(payload["full_name"], str) and payload["full_name"].strip():
        current_user.full_name = payload["full_name"].strip()[:255]
    if "phone" in payload:
        v = payload.get("phone")
        current_user.phone = (str(v).strip()[:50] if v else None)
    if "biography" in payload and up:
        v = payload.get("biography")
        up.biography = (str(v).strip()[:2000] if v else None)
    if "address" in payload and up:
        v = payload.get("address")
        up.address = (str(v).strip()[:2000] if v else None)
    if "gender" in payload and up:
        v = payload.get("gender")
        up.gender = (str(v).strip()[:30] if v else None)
    if "date_of_birth" in payload and up:
        v = payload.get("date_of_birth")
        if v:
            try:
                up.date_of_birth = datetime.fromisoformat(str(v)[:10]).date()
            except Exception:
                pass
        else:
            up.date_of_birth = None

    if "student" in roles:
        sp = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
        if sp and isinstance(payload.get("student_profile"), dict):
            spd = payload["student_profile"]
            for f in ("emergency_contact_name", "emergency_contact_phone", "emergency_contact_relation"):
                if f in spd:
                    val = spd.get(f)
                    setattr(sp, f, (str(val).strip()[:255] if val else None))

    if "lecturer" in roles:
        lp = db.query(LecturerProfile).filter(LecturerProfile.user_id == current_user.id).first()
        if lp and isinstance(payload.get("lecturer_profile"), dict):
            lpd = payload["lecturer_profile"]
            for f in ("professional_title", "professional_details", "office_location", "office_hours"):
                if f in lpd:
                    val = lpd.get(f)
                    setattr(lp, f, (str(val).strip()[:255] if val else None))

    staffp = db.query(StaffProfile).filter(StaffProfile.user_id == current_user.id).first()
    if staffp and isinstance(payload.get("staff_profile"), dict):
        stp = payload["staff_profile"]
        for f in ("job_title", "office", "responsibilities"):
            if f in stp:
                val = stp.get(f)
                setattr(staffp, f, (str(val).strip()[:500] if val else None))

    db.commit()
    log_activity(db, current_user.id, current_user.institution_id, "profile.update", "Updated profile information", ip_address=request.client.host if request.client else None)
    log_action(db, "profile.updated", user_id=current_user.id, institution_id=current_user.institution_id)
    db.commit()
    return _serialize_profile(db, current_user)


@router.post("/me/avatar")
async def upload_avatar(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _ensure_profiles(db, current_user)
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only JPG, PNG, or WEBP images are allowed")
    data = await file.read()
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Image is empty or exceeds 3MB")
    ext = ALLOWED_IMAGE_TYPES[file.content_type]
    safe_name = f"avatar_{current_user.id}_{uuid.uuid4().hex}{ext}"
    base = Path(settings.DOCUMENT_STORAGE_PATH) / "avatars"
    base.mkdir(parents=True, exist_ok=True)
    path = base / safe_name
    path.write_bytes(data)
    up = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if up and up.profile_picture_path:
        old = Path(settings.DOCUMENT_STORAGE_PATH) / up.profile_picture_path
        if old.exists() and "avatars" in str(old):
            try:
                old.unlink()
            except Exception:
                pass
    rel = f"avatars/{safe_name}"
    if up:
        up.profile_picture_path = rel
    current_user.avatar_url = f"/api/v1/profile/me/avatar/file"
    db.commit()
    log_activity(db, current_user.id, current_user.institution_id, "profile.avatar_upload", "Updated profile picture", ip_address=request.client.host if request.client else None)
    db.commit()
    return {"message": "Profile picture updated", "avatar_url": current_user.avatar_url}


@router.get("/me/avatar/file")
def get_avatar(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    up = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not up or not up.profile_picture_path:
        raise HTTPException(status_code=404, detail="No profile picture")
    path = Path(settings.DOCUMENT_STORAGE_PATH) / up.profile_picture_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(path))


@router.delete("/me/avatar")
def remove_avatar(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    up = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if up and up.profile_picture_path:
        path = Path(settings.DOCUMENT_STORAGE_PATH) / up.profile_picture_path
        if path.exists() and "avatars" in str(path):
            try:
                path.unlink()
            except Exception:
                pass
        up.profile_picture_path = None
    current_user.avatar_url = None
    db.commit()
    log_activity(db, current_user.id, current_user.institution_id, "profile.avatar_remove", "Removed profile picture", ip_address=request.client.host if request.client else None)
    db.commit()
    return {"message": "Profile picture removed"}


@router.post("/me/change-password")
def change_password(payload: dict, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current = payload.get("current_password") or ""
    new = payload.get("new_password") or ""
    if not current_user.hashed_password or not verify_password(current, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(new) < 8:
        raise HTTPException(status_code=422, detail="New password must be at least 8 characters")
    current_user.hashed_password = hash_password(new)
    create_notification(db, current_user.id, "Password changed", "Your account password was changed.", type_="security", category="security", priority="high", send_email_flag=True, to_email=current_user.email)
    log_action(db, "security.password_changed", user_id=current_user.id, institution_id=current_user.institution_id)
    log_activity(db, current_user.id, current_user.institution_id, "security.password_changed", "Password changed", ip_address=request.client.host if request.client else None)
    db.commit()
    return {"message": "Password changed successfully"}


@router.post("/me/change-email/request")
@limiter.limit(settings.RATE_LIMIT_EMAIL_CHANGE if hasattr(settings, "RATE_LIMIT_EMAIL_CHANGE") else "3/hour")
def request_email_change(payload: dict, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_email = str(payload.get("new_email") or "").strip().lower()
    if not new_email or not EMAIL_RE.match(new_email):
        raise HTTPException(status_code=422, detail="A valid new email address is required")
    if new_email == (current_user.email or "").lower():
        raise HTTPException(status_code=400, detail="New email must be different from current email")
    if db.query(User).filter(User.email == new_email, User.id != current_user.id).first():
        raise HTTPException(status_code=409, detail="Email address is already in use")
    # store pending email in settings.extra
    from app.models.user_setting import UserSetting
    setting = db.query(UserSetting).filter(UserSetting.user_id == current_user.id).first()
    if not setting:
        setting = UserSetting(user_id=current_user.id)
        db.add(setting)
        db.flush()
    extra = dict(setting.extra or {})
    extra["pending_email"] = new_email
    setting.extra = extra
    db.query(EmailVerificationToken).filter(EmailVerificationToken.user_id == current_user.id, EmailVerificationToken.used.is_(False)).delete(synchronize_session=False)
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=30)
    db.add(EmailVerificationToken(user_id=current_user.id, token=token, expires_at=expires_at, used=False))
    db.flush()
    verify_link = f"{settings.FRONTEND_BASE_URL}/verify-email-change?token={token}"
    body = (
        f"Hello {current_user.full_name},\n\n"
        f"We received a request to change your ADCS account email to {new_email}.\n"
        f"Confirm this change by opening: {verify_link}\n\n"
        "If you did not request this, you can ignore this message."
    )
    sent = False
    try:
        sent = send_email(new_email, "Confirm your new ADCS email address", body)
    except Exception:
        sent = False
    log_action(db, "security.email_change_requested", user_id=current_user.id, institution_id=current_user.institution_id, details=f"pending={new_email}")
    log_activity(db, current_user.id, current_user.institution_id, "security.email_change_requested", f"Requested email change to {new_email}", ip_address=request.client.host if request.client else None)
    create_notification(db, current_user.id, "Email change requested", f"A request to change your email to {new_email} was made. Confirm via the link sent to the new address.", type_="security", category="security", priority="high")
    db.commit()
    return {"message": "Verification link sent to the new email address." if sent else "Email change requested. If SMTP is not configured, ask an administrator to assist with verification.", "pending_email": new_email, "email_sent": sent}


@router.post("/me/change-email/confirm")
def confirm_email_change(payload: dict, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    token = (payload.get("token") or "").strip()
    if not token:
        raise HTTPException(status_code=422, detail="Verification token is required")
    rec = db.query(EmailVerificationToken).filter(EmailVerificationToken.token == token, EmailVerificationToken.user_id == current_user.id, EmailVerificationToken.used.is_(False)).first()
    if not rec or rec.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    from app.models.user_setting import UserSetting
    setting = db.query(UserSetting).filter(UserSetting.user_id == current_user.id).first()
    pending = ((setting.extra or {}).get("pending_email") if setting else None)
    if not pending or not EMAIL_RE.match(str(pending).strip().lower()):
        raise HTTPException(status_code=400, detail="No pending email change found")
    pending = str(pending).strip().lower()
    if db.query(User).filter(User.email == pending, User.id != current_user.id).first():
        raise HTTPException(status_code=409, detail="Email address is already in use")
    current_user.email = pending
    current_user.is_verified = True
    rec.used = True
    extra = dict(setting.extra or {}) if setting else {}
    extra.pop("pending_email", None)
    if setting:
        setting.extra = extra
    log_action(db, "security.email_changed", user_id=current_user.id, institution_id=current_user.institution_id, details=pending)
    log_activity(db, current_user.id, current_user.institution_id, "security.email_changed", f"Email changed to {pending}", ip_address=request.client.host if request.client else None)
    create_notification(db, current_user.id, "Email address changed", f"Your account email was changed to {pending}.", type_="security", category="security", priority="high", send_email_flag=True, to_email=pending)
    db.commit()
    return {"message": "Email address updated and verified", "email": pending}


@router.get("/me/security/sessions")
def my_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sessions = db.query(UserSession).filter(UserSession.user_id == current_user.id).order_by(UserSession.last_active_at.desc().nullslast(), UserSession.created_at.desc()).all()
    return [
        {
            "id": s.id,
            "device_info": s.device_info,
            "ip_address": s.ip_address,
            "last_active_at": s.last_active_at,
            "created_at": s.created_at,
            "expires_at": s.expires_at,
            "revoked_at": s.revoked_at,
            "is_active": s.is_active,
        }
        for s in sessions
    ]


@router.post("/me/security/sessions/revoke-others")
def revoke_other_sessions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    now = datetime.utcnow()
    updated = db.query(UserSession).filter(UserSession.user_id == current_user.id, UserSession.is_active.is_(True)).update({"is_active": False, "revoked_at": now}, synchronize_session=False)
    log_action(db, "security.sessions_revoked", user_id=current_user.id, institution_id=current_user.institution_id, details=f"revoked={updated}")
    log_activity(db, current_user.id, current_user.institution_id, "security.sessions_revoked", "Revoked other sessions")
    db.commit()
    return {"message": "Other sessions revoked", "revoked": updated}


@router.post("/me/security/sessions/{session_id}/revoke")
def revoke_session(session_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    s = db.query(UserSession).filter(UserSession.id == session_id, UserSession.user_id == current_user.id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    s.is_active = False
    s.revoked_at = datetime.utcnow()
    db.commit()
    return {"message": "Session revoked"}


@router.get("/me/security/login-history")
def login_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = db.query(LoginHistory).filter(LoginHistory.user_id == current_user.id).order_by(LoginHistory.created_at.desc()).limit(100).all()
    return [
        {
            "id": r.id,
            "success": r.success,
            "method": r.method,
            "ip_address": r.ip_address,
            "user_agent": r.user_agent,
            "failure_reason": r.failure_reason,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.get("/me/activity")
def my_activity(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = db.query(UserActivityLog).filter(UserActivityLog.user_id == current_user.id).order_by(UserActivityLog.created_at.desc()).limit(100).all()
    return [{"id": r.id, "activity_type": r.activity_type, "description": r.description, "created_at": r.created_at, "ip_address": r.ip_address} for r in rows]


@router.post("/me/correction-request")
def correction_request(payload: dict, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if "student" not in set(_roles(current_user)):
        raise HTTPException(status_code=403, detail="Only students can submit correction requests")
    subject = (payload.get("subject") or "Profile/record correction request").strip()[:255]
    details = (payload.get("details") or "").strip()
    if not details:
        raise HTTPException(status_code=422, detail="Request details are required")
    ticket = SupportTicket(
        user_id=current_user.id,
        institution_id=current_user.institution_id,
        subject=subject,
        description=details,
        category="profile_correction",
        status="open",
        priority="normal",
    )
    db.add(ticket)
    db.flush()
    db.add(SupportTicketMessage(ticket_id=ticket.id, author_id=current_user.id, body=details, is_internal=False))
    log_action(db, "profile.correction_requested", user_id=current_user.id, institution_id=current_user.institution_id, resource_type="support_ticket", resource_id=ticket.id)
    log_activity(db, current_user.id, current_user.institution_id, "profile.correction_requested", "Submitted correction request", ip_address=request.client.host if request.client else None)
    db.commit()
    return {"message": "Correction request submitted to authorized administrators", "ticket_id": ticket.id}


@router.post("/me/deactivation-request")
def deactivation_request(payload: dict, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    reason = (payload.get("reason") or "").strip()
    if not reason:
        raise HTTPException(status_code=422, detail="A reason is required")
    ticket = SupportTicket(
        user_id=current_user.id,
        institution_id=current_user.institution_id,
        subject="Account deactivation request",
        description=reason,
        category="account_deactivation",
        status="open",
        priority="high",
    )
    db.add(ticket)
    db.flush()
    db.add(SupportTicketMessage(ticket_id=ticket.id, author_id=current_user.id, body=reason, is_internal=False))
    log_action(db, "account.deactivation_requested", user_id=current_user.id, institution_id=current_user.institution_id, resource_type="support_ticket", resource_id=ticket.id)
    create_notification(db, current_user.id, "Deactivation request received", "Your account deactivation request was submitted for review.", type_="account", category="security", priority="high")
    db.commit()
    return {"message": "Deactivation request submitted for authorized review", "ticket_id": ticket.id}
