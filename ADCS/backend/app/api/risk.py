from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.deps import require_roles, ensure_institution_access
from app.models.student import Student
from app.models.student import Lecturer
from app.models.academic import Course, CourseEnrollment
from app.models.risk import RiskAssessment, RiskAlert
from app.ai.risk_engine import RiskEngine
from app.services.notification_service import create_notification
from pydantic import BaseModel, Field

router = APIRouter(prefix="/risk", tags=["Risk Assessment"])
STAFF_ROLES = {"university_admin", "registrar", "compliance_officer"}


class RiskReviewCreate(BaseModel):
    notes: str | None = Field(default=None, max_length=4000)


def _role_names(user) -> set[str]:
    return {role.name for role in user.roles}


def _ensure_risk_access(db: Session, student: Student, current_user) -> None:
    roles = _role_names(current_user)
    ensure_institution_access(current_user, student.institution_id)
    if current_user.is_superuser or "super_admin" in roles or roles.intersection(STAFF_ROLES):
        return
    if "student" in roles and student.user_id == current_user.id:
        return
    if "lecturer" in roles:
        lecturer = db.query(Lecturer).filter(
            Lecturer.user_id == current_user.id,
            Lecturer.institution_id == current_user.institution_id,
        ).first()
        if lecturer and db.query(CourseEnrollment).join(Course).filter(
            CourseEnrollment.student_id == student.id,
            CourseEnrollment.institution_id == student.institution_id,
            CourseEnrollment.status == "enrolled",
            Course.lecturer_id == lecturer.id,
            Course.institution_id == student.institution_id,
        ).first():
            return
    raise HTTPException(status_code=403, detail="No access to this student's compliance data")


@router.post("/assess/{student_id}")
def assess_student(student_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles("lecturer", "university_admin", "registrar", "compliance_officer", "super_admin"))):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    _ensure_risk_access(db, student, current_user)
    engine = RiskEngine(student.institution_id, db)
    result = engine.assess(student)
    ra = RiskAssessment(
        institution_id=student.institution_id,
        student_id=student.id,
        assessed_by=current_user.id,
        risk_score=result["risk_score"],
        risk_level=result["risk_level"],
        factors=result["factors"],
        recommendations=result["recommendations"],
        attendance_rate=result["attendance_rate"],
        missed_assessments=result["missed_assessments"],
        threshold_snapshot=result["threshold_snapshot"],
    )
    db.add(ra); db.commit(); db.refresh(ra)

    # alert if high/moderate
    if result["risk_level"] in ("moderate", "high"):
        msg = f"Student {student.student_number} assessed as {result['risk_level']} risk (score {result['risk_score']})."
        alert = RiskAlert(institution_id=student.institution_id, student_id=student.id,
                          risk_assessment_id=ra.id, level=result["risk_level"], message=msg)
        db.add(alert); db.commit()
        # notify lecturers/admins? notify current user's institution admins via in-app
        from app.models.user import User
        admins = db.query(User).filter(User.institution_id == student.institution_id).all()
        for a in admins:
            if any(r.name in ("university_admin", "compliance_officer", "registrar") for r in a.roles):
                create_notification(db, a.id, f"Risk alert: {result['risk_level']}", msg,
                                   type_="risk_alert", institution_id=student.institution_id, link=f"/students/{student.id}")
    return {"assessment_id": ra.id, **result}


@router.get("/assessments/{student_id}")
def list_assessments(student_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Not found")
    _ensure_risk_access(db, student, current_user)
    ras = db.query(RiskAssessment).filter(RiskAssessment.student_id == student_id).order_by(RiskAssessment.created_at.desc()).all()
    return [{"id": r.id, "risk_score": r.risk_score, "risk_level": r.risk_level, "factors": r.factors,
             "recommendations": r.recommendations, "attendance_rate": r.attendance_rate,
             "missed_assessments": r.missed_assessments, "reviewed": r.reviewed, "created_at": str(r.created_at)} for r in ras]


@router.post("/assessments/{assessment_id}/review")
def review_assessment(assessment_id: int, payload: RiskReviewCreate, db: Session = Depends(get_db), current_user=Depends(require_roles("lecturer", "university_admin", "compliance_officer", "super_admin"))):
    ra = db.query(RiskAssessment).filter(RiskAssessment.id == assessment_id).first()
    if not ra:
        raise HTTPException(status_code=404, detail="Not found")
    ensure_institution_access(current_user, ra.institution_id)
    student = db.query(Student).filter(Student.id == ra.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if "lecturer" in _role_names(current_user) and not _role_names(current_user).intersection(STAFF_ROLES):
        _ensure_risk_access(db, student, current_user)
    ra.reviewed = True
    ra.reviewed_by = current_user.id
    from datetime import datetime as dt
    ra.reviewed_at = dt.utcnow()
    ra.review_notes = payload.notes
    db.commit()
    return {"id": ra.id, "reviewed": True}


@router.get("/alerts")
def list_alerts(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    roles = _role_names(current_user)
    q = db.query(RiskAlert)
    if current_user.is_superuser or "super_admin" in roles:
        pass
    elif roles.intersection(STAFF_ROLES):
        q = q.filter(RiskAlert.institution_id == current_user.institution_id)
    elif "student" in roles:
        q = q.filter(
            RiskAlert.institution_id == current_user.institution_id,
            RiskAlert.student_id.in_(
                db.query(Student.id).filter(Student.user_id == current_user.id)
            ),
        )
    elif "lecturer" in roles:
        lecturer = db.query(Lecturer).filter(
            Lecturer.user_id == current_user.id,
            Lecturer.institution_id == current_user.institution_id,
        ).first()
        if not lecturer:
            return []
        q = q.filter(
            RiskAlert.institution_id == current_user.institution_id,
            RiskAlert.student_id.in_(
                db.query(CourseEnrollment.student_id)
                .join(Course)
                .filter(
                    Course.lecturer_id == lecturer.id,
                    Course.institution_id == current_user.institution_id,
                    CourseEnrollment.status == "enrolled",
                )
            ),
        )
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return [{"id": a.id, "student_id": a.student_id, "level": a.level, "message": a.message,
             "is_read": a.is_read, "created_at": str(a.created_at)} for a in q.all()]


@router.patch("/alerts/{alert_id}/read")
def read_alert(alert_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    a = db.query(RiskAlert).filter(RiskAlert.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Not found")
    student = db.query(Student).filter(Student.id == a.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    _ensure_risk_access(db, student, current_user)
    a.is_read = True
    a.read_by = current_user.id
    from datetime import datetime as dt
    a.read_at = dt.utcnow()
    db.commit()
    return {"id": a.id, "is_read": True}
