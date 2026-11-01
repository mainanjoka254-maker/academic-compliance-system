from sqlalchemy.orm import Session
from typing import Optional

from app.models.notification import Notification
from app.services.email_service import send_email


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
) -> Notification:
    notif = Notification(
        user_id=user_id,
        institution_id=institution_id,
        type=type_,
        title=title,
        message=message,
        link=link,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    if send_email_flag and to_email:
        # Email failure must not corrupt DB transaction (already committed)
        try:
            send_email(to_email, title, message)
        except Exception:
            pass
    return notif
