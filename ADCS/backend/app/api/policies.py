from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.deps import require_roles, ensure_institution_access
from app.models.compliance import AcademicPolicy, ComplianceRule
from app.models.compliance_case import Appeal, ComplianceCase
from app.models.student import Student
from app.models.institution import Institution
from app.core.deps import is_super_admin
from app.models.user import User
from app.schemas.compliance import AcademicPolicyCreate, ComplianceRuleCreate, AppealCreate

router = APIRouter(prefix="/compliance", tags=["Compliance"])


def _institution_for_write(db: Session, current_user: User, requested_id: int | None) -> int:
    if is_super_admin(current_user):
        institution_id = requested_id
    else:
        institution_id = current_user.institution_id
        if requested_id is not None and requested_id != institution_id:
            raise HTTPException(status_code=403, detail="Cross-institution access denied")
    if institution_id is None or not db.query(Institution.id).filter(
        Institution.id == institution_id,
        Institution.is_active.is_(True),
    ).first():
        raise HTTPException(status_code=400, detail="An active institution is required")
    return institution_id


@router.post("/policies", status_code=201)
def create_policy(payload: AcademicPolicyCreate, db: Session = Depends(get_db), current_user=Depends(require_roles("university_admin", "super_admin"))):
    institution_id = _institution_for_write(db, current_user, payload.institution_id)
    p = AcademicPolicy(institution_id=institution_id, title=payload.title,
                       content=payload.content, code=payload.code, category=payload.category,
                       version=payload.version, effective_date=payload.effective_date,
                       is_active=payload.is_active)
    db.add(p); db.commit(); db.refresh(p)
    return {"id": p.id, "title": p.title}


@router.get("/policies")
def list_policies(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    q = db.query(AcademicPolicy)
    if not (current_user.is_superuser or any(r.name == "super_admin" for r in current_user.roles)):
        q = q.filter(AcademicPolicy.institution_id == current_user.institution_id)
    return [{"id": p.id, "title": p.title, "content": p.content, "category": p.category, "version": p.version, "is_active": p.is_active} for p in q.all()]


@router.post("/rules", status_code=201)
def create_rule(payload: ComplianceRuleCreate, db: Session = Depends(get_db), current_user=Depends(require_roles("university_admin", "super_admin"))):
    institution_id = _institution_for_write(db, current_user, payload.institution_id)
    r = ComplianceRule(institution_id=institution_id, name=payload.name,
                       rule_type=payload.rule_type, description=payload.description,
                       code=payload.code, threshold_value=payload.threshold_value,
                       weight=payload.weight, severity=payload.severity,
                       is_active=payload.is_active)
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id, "name": r.name}


@router.get("/rules")
def list_rules(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    q = db.query(ComplianceRule)
    if not (current_user.is_superuser or any(r.name == "super_admin" for r in current_user.roles)):
        q = q.filter(ComplianceRule.institution_id == current_user.institution_id)
    return [{"id": r.id, "name": r.name, "rule_type": r.rule_type, "threshold_value": r.threshold_value,
             "weight": r.weight, "is_active": r.is_active} for r in q.all()]


@router.post("/appeals", status_code=201)
def create_appeal(payload: AppealCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    case = db.query(ComplianceCase).filter(ComplianceCase.id == payload.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    stu = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not stu or stu.id != case.student_id:
        raise HTTPException(status_code=403, detail="Only affected student may appeal")
    appeal = Appeal(institution_id=case.institution_id, case_id=case.id, student_id=stu.id,
                    submitted_by=current_user.id, content=payload.content)
    db.add(appeal); db.commit(); db.refresh(appeal)
    case.status = "awaiting_response"; db.commit()
    return {"id": appeal.id}


@router.get("/appeals")
def list_appeals(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    q = db.query(Appeal)
    roles = {role.name for role in current_user.roles}
    if is_super_admin(current_user):
        pass
    elif current_user.institution_id is None:
        raise HTTPException(status_code=403, detail="An institution is required")
    elif roles.intersection({"university_admin", "registrar", "compliance_officer"}):
        q = q.filter(Appeal.institution_id == current_user.institution_id)
    elif "student" in roles:
        student = db.query(Student).filter(
            Student.user_id == current_user.id,
            Student.institution_id == current_user.institution_id,
        ).first()
        q = q.filter(Appeal.student_id == student.id) if student else q.filter(False)
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return [{"id": a.id, "case_id": a.case_id, "student_id": a.student_id, "status": a.status,
             "content": a.content, "response": a.response, "created_at": str(a.created_at)} for a in q.all()]
