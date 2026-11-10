from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.notification import Notification

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _serialize(n: Notification):
    return {
        "id": n.id,
        "user_id": n.user_id,
        "institution_id": n.institution_id,
        "type": n.type,
        "category": n.category or n.type,
        "priority": n.priority or "normal",
        "title": n.title,
        "message": n.message,
        "link": n.link,
        "related_type": n.related_type,
        "related_id": n.related_id,
        "is_read": n.is_read,
        "read_at": n.read_at,
        "is_archived": n.is_archived,
        "archived_at": n.archived_at,
        "delivery_status": n.delivery_status,
        "created_at": n.created_at,
    }


@router.get("")
def list_notifications(
    category: Optional[str] = Query(default=None),
    unread: Optional[bool] = Query(default=None),
    archived: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    format: str = Query(default="list"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_archived == archived)
    if category:
        q = q.filter((Notification.category == category) | (Notification.type == category))
    if unread is True:
        q = q.filter(Notification.is_read.is_(False))
    if unread is False:
        q = q.filter(Notification.is_read.is_(True))
    items = q.order_by(Notification.created_at.desc()).limit(limit).all()
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False),
        Notification.is_archived.is_(False),
    ).count()
    serialized = [_serialize(n) for n in items]
    if format == "center":
        return {"items": serialized, "unread_count": unread_count}
    return serialized


@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False),
        Notification.is_archived.is_(False),
    ).count()
    return {"unread_count": count}


@router.patch("/{nid}/read")
def read_notification(nid: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    n = db.query(Notification).filter(Notification.id == nid, Notification.user_id == current_user.id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Not found")
    if not n.is_read:
        n.is_read = True
        n.read_at = datetime.utcnow()
        db.commit()
    return _serialize(n)


@router.post("/read-all")
def read_all(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    now = datetime.utcnow()
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False),
        Notification.is_archived.is_(False),
    ).update({"is_read": True, "read_at": now}, synchronize_session=False)
    db.commit()
    return {"message": "ok"}


@router.post("/{nid}/archive")
def archive_notification(nid: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    n = db.query(Notification).filter(Notification.id == nid, Notification.user_id == current_user.id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Not found")
    n.is_archived = True
    n.archived_at = datetime.utcnow()
    db.commit()
    return _serialize(n)


@router.post("/{nid}/unarchive")
def unarchive_notification(nid: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    n = db.query(Notification).filter(Notification.id == nid, Notification.user_id == current_user.id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Not found")
    n.is_archived = False
    n.archived_at = None
    db.commit()
    return _serialize(n)
