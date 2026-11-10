from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user_setting import UserSetting, UserNotificationPreference, UserPrivacyPreference

router = APIRouter(prefix="/settings", tags=["Settings"])


def _get_or_create(db: Session, model, user_id: int):
    obj = db.query(model).filter(model.user_id == user_id).first()
    if not obj:
        obj = model(user_id=user_id)
        db.add(obj)
        db.flush()
    return obj


def _serialize(s: UserSetting, n: UserNotificationPreference, p: UserPrivacyPreference):
    return {
        "theme": s.theme,
        "language": s.language,
        "timezone": s.timezone,
        "date_format": getattr(s, "date_format", "YYYY-MM-DD"),
        "font_size": getattr(s, "font_size", "medium"),
        "email_notifications": s.email_notifications,
        "in_app_notifications": s.in_app_notifications,
        "dashboard_preferences": s.dashboard_preferences or {},
        "privacy_preferences": s.privacy_preferences or {},
        "extra": s.extra or {},
        "notification_preferences": {
            "academic_announcements": n.academic_announcements,
            "course_notifications": n.course_notifications,
            "registration_notifications": n.registration_notifications,
            "attendance_alerts": n.attendance_alerts,
            "compliance_alerts": n.compliance_alerts,
            "assessment_notifications": n.assessment_notifications,
            "security_notifications": n.security_notifications,
            "email_enabled": n.email_enabled,
            "in_app_enabled": n.in_app_enabled,
            "frequency": n.frequency,
        },
        "privacy": {
            "show_profile_picture": p.show_profile_picture,
            "show_email": p.show_email,
            "show_phone": p.show_phone,
            "allow_contact": p.allow_contact,
        },
    }


@router.get("/me")
def get_settings(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    s = _get_or_create(db, UserSetting, current_user.id)
    n = _get_or_create(db, UserNotificationPreference, current_user.id)
    p = _get_or_create(db, UserPrivacyPreference, current_user.id)
    db.commit()
    db.refresh(s); db.refresh(n); db.refresh(p)
    return _serialize(s, n, p)


@router.patch("/me")
def update_settings(payload: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    s = _get_or_create(db, UserSetting, current_user.id)
    n = _get_or_create(db, UserNotificationPreference, current_user.id)
    p = _get_or_create(db, UserPrivacyPreference, current_user.id)

    for field in ("theme", "language", "timezone", "date_format", "font_size"):
        if field in payload and hasattr(s, field):
            setattr(s, field, payload[field])
    for field in ("email_notifications", "in_app_notifications"):
        if field in payload:
            setattr(s, field, bool(payload[field]))
            setattr(n, "email_enabled" if field == "email_notifications" else "in_app_enabled", bool(payload[field]))
    for field in ("extra", "dashboard_preferences", "privacy_preferences"):
        if field in payload and isinstance(payload[field], dict):
            setattr(s, field, {**(getattr(s, field) or {}), **payload[field]})

    np = payload.get("notification_preferences") or {}
    for field in ("academic_announcements", "course_notifications", "registration_notifications", "attendance_alerts", "compliance_alerts", "assessment_notifications", "security_notifications", "email_enabled", "in_app_enabled"):
        if field in np:
            setattr(n, field, bool(np[field]))
    if "frequency" in np:
        n.frequency = str(np["frequency"])

    priv = payload.get("privacy") or {}
    for field in ("show_profile_picture", "show_email", "show_phone", "allow_contact"):
        if field in priv:
            setattr(p, field, bool(priv[field]))

    s.updated_at = datetime.utcnow()
    n.updated_at = datetime.utcnow()
    p.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(s); db.refresh(n); db.refresh(p)
    return _serialize(s, n, p)