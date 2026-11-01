from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.deps import ensure_institution_access, is_super_admin
from app.models.compliance import ComplianceIncident
from app.models.academic import Course, CourseEnrollment
from app.models.student import Lecturer, Student
from app.models.user import User
from app.schemas.compliance import ComplianceIncidentCreate

router = APIRouter(prefix="/compliance", tags=["Compliance"])
STAFF_ROLES = {"university_admin", "registrar", "compliance_officer"}


def _role_names(user: User) -> set[str]:
    return {role.name for role in user.roles}


def _can_access_student(db: Session, user: User, student: Student) -> bool:
    roles = _role_names(user)
    if is_super_admin(user):
        return True
    if user.institution_id != student.institution_id:
        return False
    if roles.intersection(STAFF_ROLES):
        return True
    if "student" in roles:
        return user.id == student.user_id
    if "lecturer" in roles:
        lecturer = db.query(Lecturer).filter(
            Lecturer.user_id == user.id,
            Lecturer.institution_id == user.institution_id,
        ).first()
        return bool(lecturer and db.query(CourseEnrollment).join(Course).filter(
            CourseEnrollment.student_id == student.id,
            CourseEnrollment.status == "enrolled",
            Course.lecturer_id == lecturer.id,
            Course.institution_id == student.institution_id,
        ).first())
    return False


@router.post("/incidents", status_code=201)
def create_incident(payload: ComplianceIncidentCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    roles = _role_names(current_user)
    if not (is_super_admin(current_user) or roles.intersection(STAFF_ROLES | {"lecturer", "student"})):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    student = db.query(Student).filter(Student.id == payload.student_id).first() if payload.student_id else None
    if payload.student_id is not None and not student:
        raise HTTPException(status_code=404, detail="Student not found")
    course = db.query(Course).filter(Course.id == payload.course_id).first() if payload.course_id else None
    if payload.course_id is not None and not course:
        raise HTTPException(status_code=404, detail="Course not found")

    inst_id = payload.institution_id
    if student:
        if not _can_access_student(db, current_user, student):
            raise HTTPException(status_code=403, detail="No permission to report this student's incident")
        inst_id = student.institution_id
    elif course:
        inst_id = course.institution_id
    elif not is_super_admin(current_user):
        inst_id = current_user.institution_id
    if inst_id is None:
        raise HTTPException(status_code=422, detail="institution_id is required for a platform-level incident")
    ensure_institution_access(current_user, inst_id)
    if student and student.institution_id != inst_id:
        raise HTTPException(status_code=400, detail="Student does not belong to the selected institution")
    if course and course.institution_id != inst_id:
        raise HTTPException(status_code=400, detail="Course does not belong to the selected institution")
    if student and course:
        if course.institution_id != student.institution_id:
            raise HTTPException(status_code=400, detail="Course and student must belong to the same institution")
    if "student" in roles and not roles.intersection(STAFF_ROLES):
        if not student or student.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Students may report incidents only for their own profile")
    if "lecturer" in roles and not roles.intersection(STAFF_ROLES):
        lecturer = db.query(Lecturer).filter(
            Lecturer.user_id == current_user.id,
            Lecturer.institution_id == inst_id,
        ).first()
        if not course or not lecturer or course.lecturer_id != lecturer.id:
            raise HTTPException(status_code=403, detail="Lecturers may report only for an assigned course")

    inc = ComplianceIncident(institution_id=inst_id, reported_by=current_user.id,
                            incident_type=payload.incident_type,
                            title=payload.title,
                            description=payload.description,
                            evidence=payload.evidence,
                            priority=payload.priority,
                            student_id=student.id if student else None,
                            course_id=course.id if course else None)
    db.add(inc); db.commit(); db.refresh(inc)
    return {"id": inc.id, "title": inc.title, "status": inc.status}


@router.get("/incidents")
def list_incidents(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    q = db.query(ComplianceIncident)
    roles = _role_names(current_user)
    if is_super_admin(current_user):
        pass
    elif current_user.institution_id is None:
        raise HTTPException(status_code=403, detail="An institution is required")
    elif roles.intersection(STAFF_ROLES):
        q = q.filter(ComplianceIncident.institution_id == current_user.institution_id)
    elif "student" in roles:
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        q = q.filter(
            ComplianceIncident.institution_id == current_user.institution_id,
            (ComplianceIncident.reported_by == current_user.id)
            | (ComplianceIncident.student_id == (student.id if student else -1)),
        )
    elif "lecturer" in roles:
        lecturer = db.query(Lecturer).filter(
            Lecturer.user_id == current_user.id,
            Lecturer.institution_id == current_user.institution_id,
        ).first()
        if not lecturer:
            return []
        q = q.filter(
            ComplianceIncident.institution_id == current_user.institution_id,
            (ComplianceIncident.reported_by == current_user.id)
            | (ComplianceIncident.course_id.in_(
                db.query(Course.id).filter(Course.lecturer_id == lecturer.id)
            )),
        )
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return [{"id": i.id, "institution_id": i.institution_id, "student_id": i.student_id, "incident_type": i.incident_type,
             "title": i.title, "status": i.status, "priority": i.priority, "created_at": str(i.created_at)} for i in q.all()]
