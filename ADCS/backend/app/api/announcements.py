from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.announcement import Announcement
from app.models.user import User
from app.models.role import Role
from app.services.notification_service import create_notification

router = APIRouter(prefix="/announcements", tags=["Announcements"])


@router.get("")
def list_announcements(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    now = datetime.utcnow()
    q = db.query(Announcement).filter(Announcement.is_active.is_(True))
    if current_user.institution_id is not None and not current_user.is_superuser:
        q = q.filter((Announcement.institution_id == current_user.institution_id) | (Announcement.institution_id.is_(None)))
    items = []
    for a in q.order_by(Announcement.created_at.desc()).all():
        if a.starts_at and a.starts_at > now:
            continue
        if a.expires_at and a.expires_at < now:
            continue
        items.append({"id": a.id, "title": a.title, "body": a.body, "audience": a.audience,
                      "created_at": a.created_at, "author_id": a.author_id})
    return items


@router.post("", status_code=201)
def create_announcement(payload: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    roles = {r.name for r in current_user.roles}
    if not (current_user.is_superuser or roles.intersection({"university_admin", "super_admin", "registrar"})):
        raise HTTPException(status_code=403, detail="Not authorized")
    a = Announcement(
        institution_id=current_user.institution_id,
        author_id=current_user.id,
        title=(payload.get("title") or "")[:255],
        body=(payload.get("body") or ""),
        audience=(payload.get("audience") or "all"),
    )
    db.add(a)
    db.flush()
    # notify audience (in-app, real event)
    uq = db.query(User).filter(User.is_active.is_(True))
    if not current_user.is_superuser and current_user.institution_id:
        uq = uq.filter((User.institution_id == current_user.institution_id) | (User.institution_id.is_(None)))
    if a.audience and a.audience != "all":
        uq = uq.join(User.roles).filter(Role.name == a.audience)
    recipients = uq.all()
    seen = set()
    for u in recipients:
        if u.id in seen:
            continue
        seen.add(u.id)
        try:
            create_notification(db, u.id, f"Announcement: {a.title}", (a.body or "")[:500], type_="announcement", institution_id=a.institution_id or u.institution_id, category="announcement", priority="normal", related_type="announcement", related_id=a.id)
        except Exception:
            pass
    db.commit()
    db.refresh(a)
    return {"id": a.id, "title": a.title}