from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.support_ticket import SupportTicket

router = APIRouter(prefix="/support", tags=["Support"])


@router.get("/tickets")
def list_tickets(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    q = db.query(SupportTicket)
    if not current_user.is_superuser:
        q = q.filter(SupportTicket.user_id == current_user.id)
    return [{"id": t.id, "subject": t.subject, "status": t.status, "priority": t.priority,
             "created_at": t.created_at} for t in q.order_by(SupportTicket.created_at.desc()).all()]


@router.post("/tickets", status_code=201)
def create_ticket(payload: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    t = SupportTicket(
        user_id=current_user.id,
        institution_id=current_user.institution_id,
        subject=payload.get("subject", ""),
        description=payload.get("description", ""),
        priority=payload.get("priority", "normal"),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id, "status": t.status}