from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationDelivery
from app.models.user import User
from app.models.user_setting import UserNotificationPreference
from app.services.email_service import send_email


CATEGORY_DEFAULTS = {
    "account_verification": "security",
    "password_reset": "security",
    "account_approval": "registration",
    "compliance_warning": "compliance",
    "risk_alert": "compliance",
    "attendance_concern": "attendance",
    "missed_deadline": "academic",
    "new_case": "compliance",
    "investigation_update": "compliance",
    "appeal_response": "compliance",
    "document_review": "academic",
}


def _prefs(db: Session, user_id: int) -> UserNotificationPreference:
    prefs = db.query(UserNotificationPreference).filter(UserNotificationPreference.user_id == user_id).first()
    if not prefs:
        prefs = UserNotificationPreference(user_id=user_id)
        db.add(prefs)
        db.flush()
    return prefs


def _category_enabled(prefs: UserNotificationPreference, category: str) -> bool:
    mapping = {
        "announcement": prefs.academic_announcements,
        "academic": prefs.academic_announcements,
        "course": prefs.course_notifications,
        "registration": prefs.registration_notifications,
        "attendance": prefs.attendance_alerts,
        "compliance": prefs.compliance_alerts,
        "assessment": prefs.assessment_notifications,
        "security": prefs.security_notifications,
    }
    return mapping.get(category, True)


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    type_: str = "compliance_warning",
    institution_id: Optional[int] = None,
    link: Optional[str] = None,
    send_email_flag: bool = False,
    to_email: Optional[str] = None,
    category: Optional[str] = None,
    priority: str = "normal",
    related_type: Optional[str] = None,
    related_id: Optional[int] = None,
) -> Notification:
    user = db.query(User).filter(User.id == user_id).first()
    prefs = _prefs(db, user_id)
    resolved_category = category or CATEGORY_DEFAULTS.get(type_, "general")
    in_app_enabled = prefs.in_app_enabled and _category_enabled(prefs, resolved_category)
    email_enabled = prefs.email_enabled and _category_enabled(prefs, resolved_category)

    notif = Notification(
        user_id=user_id,
        institution_id=institution_id or (user.institution_id if user else None),
        type=type_,
        category=resolved_category,
        priority=priority,
        title=title,
        message=message,
        link=link,
        related_type=related_type,
        related_id=related_id,
        is_read=not in_app_enabled,
        read_at=datetime.utcnow() if not in_app_enabled else None,
        delivery_status="in_app" if in_app_enabled else "suppressed",
    )
    db.add(notif)
    db.flush()

    recipient = to_email or (user.email if user else None)
    should_email = bool(send_email_flag and recipient and email_enabled)
    if send_email_flag and recipient:
        delivery = NotificationDelivery(
            notification_id=notif.id,
            user_id=user_id,
            channel="email",
            status="pending",
            recipient=recipient,
            attempt_count=0,
        )
        if not email_enabled:
            delivery.status = "skipped"
            delivery.last_error = "Disabled by user notification preferences"
            notif.delivery_status = "suppressed" if not in_app_enabled else "in_app"
        elif should_email:
            delivery.attempt_count = 1
            delivery.last_attempt_at = datetime.utcnow()
            ok = False
            try:
                ok = send_email(recipient, title, message)
            except Exception as exc:
                delivery.last_error = str(exc)[:500]
            if ok:
                delivery.status = "sent"
                delivery.delivered_at = datetime.utcnow()
                notif.delivery_status = "delivered" if in_app_enabled else "email_only"
            else:
                delivery.status = "failed"
                delivery.last_error = delivery.last_error or "SMTP delivery failed"
                notif.delivery_status = "email_failed"
        db.add(delivery)

    db.commit()
    db.refresh(notif)
    return notif
