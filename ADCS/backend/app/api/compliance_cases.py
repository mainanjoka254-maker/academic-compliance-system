from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.deps import require_roles, ensure_institution_access
from app.models.compliance_case import ComplianceCase, CaseAudit
from app.models.student import Lecturer, Student
from app.models.academic import Course, CourseEnrollment
from app.models.compliance import ComplianceIncident
from app.models.user import User
from app.schemas.compliance import ComplianceCaseCreate, ComplianceCaseUpdate

router = APIRouter(prefix="/compliance", tags=["Compliance"])
STAFF_ROLES = {"university_admin", "registrar", "compliance_officer"}


def _role_names(user: User) -> set[str]:
    return {role.name for role in user.roles}


def _case_query_for_user(db: Session, current_user: User):
    query = db.query(ComplianceCase)
    roles = _role_names(current_user)
    if current_user.is_superuser or "super_admin" in roles:
        return query
    if current_user.institution_id is None:
        raise HTTPException(status_code=403, detail="An institution is required")
    query = query.filter(ComplianceCase.institution_id == current_user.institution_id)
    if roles.intersection(STAFF_ROLES):
        return query
    if "student" in roles:
        student = db.query(Student).filter(
            Student.user_id == current_user.id,
            Student.institution_id == current_user.institution_id,
        ).first()
        return query.filter(ComplianceCase.student_id == student.id) if student else query.filter(False)
    if "lecturer" in roles:
        lecturer = db.query(Lecturer).filter(
            Lecturer.user_id == current_user.id,
            Lecturer.institution_id == current_user.institution_id,
        ).first()
        if not lecturer:
            return query.filter(False)
        student_ids = db.query(CourseEnrollment.student_id).join(Course).filter(
            Course.lecturer_id == lecturer.id,
            Course.institution_id == current_user.institution_id,
            CourseEnrollment.status == "enrolled",
        )
        return query.filter(ComplianceCase.student_id.in_(student_ids))
    raise HTTPException(status_code=403, detail="Insufficient permissions")


@router.post("/cases", status_code=201)
def create_case(payload: ComplianceCaseCreate, db: Session = Depends(get_db), current_user=Depends(require_roles("compliance_officer", "university_admin", "registrar", "super_admin"))):
    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    ensure_institution_access(current_user, student.institution_id)
    if payload.incident_id is not None:
        incident = db.query(ComplianceIncident).filter(ComplianceIncident.id == payload.incident_id).first()
        if not incident or incident.institution_id != student.institution_id:
            raise HTTPException(status_code=400, detail="Incident must belong to the student's institution")
        if incident.student_id not in (None, student.id):
            raise HTTPException(status_code=400, detail="Incident is associated with another student")
    if payload.assigned_officer_id is not None:
        officer = db.query(User).filter(User.id == payload.assigned_officer_id).first()
        if (
            not officer
            or officer.institution_id != student.institution_id
            or not _role_names(officer).intersection({"university_admin", "compliance_officer", "registrar"})
        ):
            raise HTTPException(status_code=400, detail="Assigned officer must be authorized in the student's institution")
    case = ComplianceCase(institution_id=student.institution_id, case_number=f"CASE-{uuid.uuid4().hex[:8].upper()}",
                          student_id=student.id, title=payload.title,
                          description=payload.description, priority=payload.priority,
                          incident_id=payload.incident_id, assigned_officer_id=payload.assigned_officer_id)
    db.add(case); db.commit(); db.refresh(case)
    audit = CaseAudit(institution_id=student.institution_id, case_id=case.id, actor_id=current_user.id, action="case_created", details=case.title)
    db.add(audit); db.commit()
    return {"id": case.id, "case_number": case.case_number, "status": case.status}


@router.get("/cases")
def list_cases(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    q = _case_query_for_user(db, current_user)
    return [{"id": c.id, "case_number": c.case_number, "student_id": c.student_id, "title": c.title,
             "status": c.status, "priority": c.priority, "created_at": str(c.created_at)} for c in q.all()]


@router.get("/cases/{case_id}")
def get_case(case_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    c = _case_query_for_user(db, current_user).filter(ComplianceCase.id == case_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    return {"id": c.id, "case_number": c.case_number, "student_id": c.student_id, "title": c.title,
            "description": c.description, "status": c.status, "priority": c.priority,
            "decision": c.decision, "resolution_notes": c.resolution_notes}


@router.patch("/cases/{case_id}")
def update_case(case_id: int, payload: ComplianceCaseUpdate, db: Session = Depends(get_db), current_user=Depends(require_roles("compliance_officer", "university_admin", "super_admin"))):
    from app.models.compliance_case import ComplianceCase, CaseAudit
    c = db.query(ComplianceCase).filter(ComplianceCase.id == case_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    ensure_institution_access(current_user, c.institution_id)
    changes = payload.model_dump(exclude_unset=True)
    if payload.assigned_officer_id is not None:
        officer = db.query(User).filter(User.id == payload.assigned_officer_id).first()
        if (
            not officer
            or officer.institution_id != c.institution_id
            or not _role_names(officer).intersection({"university_admin", "compliance_officer", "registrar"})
        ):
            raise HTTPException(status_code=400, detail="Assigned officer must be authorized in the case's institution")
    if "status" in changes:
        c.status = payload.status
        if payload.status in ("resolved", "closed"):
            c.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if payload.status == "escalated":
            c.escalated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if "priority" in changes: c.priority = payload.priority
    if "assigned_officer_id" in changes: c.assigned_officer_id = payload.assigned_officer_id
    if "decision" in changes: c.decision = payload.decision
    if "resolution_notes" in changes: c.resolution_notes = payload.resolution_notes
    db.commit()
    audit = CaseAudit(institution_id=c.institution_id, case_id=c.id, actor_id=current_user.id, action="case_updated", details=str(payload))
    db.add(audit); db.commit()
    return {"id": c.id, "status": c.status}
