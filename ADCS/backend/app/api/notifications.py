from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.notification import Notification

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
def list_notifications(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    q = db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc())
    return [{"id": n.id, "type": n.type, "title": n.title, "message": n.message, "link": n.link,
             "is_read": n.is_read, "created_at": str(n.created_at)} for n in q.all()]


@router.patch("/{nid}/read")
def read_notification(nid: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    n = db.query(Notification).filter(Notification.id == nid, Notification.user_id == current_user.id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Not found")
    n.is_read = True
    from datetime import datetime as dt
    n.read_at = dt.utcnow()
    db.commit()
    return {"id": n.id, "is_read": True}


@router.post("/read-all")
def read_all(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_read == False).update({"is_read": True})
    db.commit()
    return {"message": "ok"}
