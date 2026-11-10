from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.support_ticket import SupportTicket, SupportTicketMessage
from app.models.user import User
from app.services.audit_service import log_action

router = APIRouter(prefix="/support", tags=["Support"])

STAFF_ROLES = {"super_admin", "university_admin", "registrar", "compliance_officer"}


def _can_manage(user: User) -> bool:
    return user.is_superuser or any(r.name in STAFF_ROLES for r in user.roles)


def _serialize(t: SupportTicket):
    return {
        "id": t.id,
        "user_id": t.user_id,
        "institution_id": t.institution_id,
        "subject": t.subject,
        "description": t.description,
        "category": getattr(t, "category", "general"),
        "status": t.status,
        "priority": t.priority,
        "resolution_note": getattr(t, "resolution_note", None),
        "created_at": t.created_at,
        "updated_at": t.updated_at,
        "closed_at": getattr(t, "closed_at", None),
    }


@router.get("/tickets")
def list_tickets(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    q = db.query(SupportTicket)
    if not _can_manage(current_user):
        q = q.filter(SupportTicket.user_id == current_user.id)
    elif not current_user.is_superuser and current_user.institution_id:
        q = q.filter((SupportTicket.institution_id == current_user.institution_id) | (SupportTicket.user_id == current_user.id))
    return [_serialize(t) for t in q.order_by(SupportTicket.created_at.desc()).all()]


@router.post("/tickets", status_code=201)
def create_ticket(payload: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    subject = (payload.get("subject") or "").strip()
    description = (payload.get("description") or "").strip()
    if not subject or not description:
        raise HTTPException(status_code=422, detail="Subject and description are required")
    t = SupportTicket(
        user_id=current_user.id,
        institution_id=current_user.institution_id,
        subject=subject[:255],
        description=description,
        category=(payload.get("category") or "general")[:50],
        priority=(payload.get("priority") or "normal")[:20],
        status="open",
    )
    db.add(t)
    db.flush()
    db.add(SupportTicketMessage(ticket_id=t.id, author_id=current_user.id, body=description, is_internal=False))
    db.commit()
    db.refresh(t)
    return _serialize(t)


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    t = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Not found")
    if not (_can_manage(current_user) or t.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    messages = db.query(SupportTicketMessage).filter(SupportTicketMessage.ticket_id == t.id).order_by(SupportTicketMessage.created_at.asc()).all()
    return {**_serialize(t), "messages": [{"id": m.id, "author_id": m.author_id, "body": m.body, "is_internal": m.is_internal, "created_at": m.created_at} for m in messages if (not m.is_internal or _can_manage(current_user))]}


@router.post("/tickets/{ticket_id}/messages", status_code=201)
def add_message(ticket_id: int, payload: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    t = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Not found")
    if not (_can_manage(current_user) or t.user_id == current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    body = (payload.get("body") or "").strip()
    if not body:
        raise HTTPException(status_code=422, detail="Message body is required")
    is_internal = bool(payload.get("is_internal") and _can_manage(current_user))
    msg = SupportTicketMessage(ticket_id=t.id, author_id=current_user.id, body=body, is_internal=is_internal)
    t.updated_at = datetime.utcnow()
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"id": msg.id, "body": msg.body, "created_at": msg.created_at}


@router.patch("/tickets/{ticket_id}")
def update_ticket(ticket_id: int, payload: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    t = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Not found")
    if not _can_manage(current_user):
        raise HTTPException(status_code=403, detail="Only authorized staff can update ticket status")
    if "status" in payload:
        t.status = str(payload["status"])[:30]
        if t.status in {"resolved", "closed"}:
            t.closed_at = datetime.utcnow()
        else:
            t.closed_at = None
    if "priority" in payload:
        t.priority = str(payload["priority"])[:20]
    if "resolution_note" in payload:
        t.resolution_note = (payload.get("resolution_note") or "")[:4000] or None
    if "assigned_to_id" in payload:
        t.assigned_to_id = payload.get("assigned_to_id")
    t.updated_at = datetime.utcnow()
    db.commit()
    log_action(db, "support_ticket.updated", user_id=current_user.id, institution_id=t.institution_id, resource_type="support_ticket", resource_id=t.id, details=t.status)
    return _serialize(t)