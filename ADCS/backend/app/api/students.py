from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.deps import require_roles
from app.models.student import Lecturer, Student
from app.models.user import User
from app.models.academic import Course, CourseEnrollment
from app.schemas.academic import StudentCreate, StudentOut

router = APIRouter(prefix="/students", tags=["Students"])


def _role_names(user: User) -> set[str]:
    return {role.name for role in user.roles}


def _lecturer_student_query(db: Session, current_user: User):
    lecturer = db.query(Lecturer).filter(Lecturer.user_id == current_user.id).first()
    if not lecturer:
        return None
    return (
        db.query(Student)
        .join(CourseEnrollment, CourseEnrollment.student_id == Student.id)
        .join(Course, Course.id == CourseEnrollment.course_id)
        .filter(
            Course.lecturer_id == lecturer.id,
            Course.institution_id == current_user.institution_id,
            Student.institution_id == current_user.institution_id,
            CourseEnrollment.status == "enrolled",
        )
        .distinct()
    )


def _ensure_student_access(db: Session, student: Student, current_user: User) -> None:
    roles = _role_names(current_user)
    if current_user.is_superuser or "super_admin" in roles:
        return
    if current_user.institution_id != student.institution_id:
        raise HTTPException(status_code=403, detail="Cross-institution access denied")
    if roles.intersection({"university_admin", "registrar", "compliance_officer"}):
        return
    if "lecturer" in roles:
        query = _lecturer_student_query(db, current_user)
        if query is not None and query.filter(Student.id == student.id).first():
            return
        raise HTTPException(status_code=403, detail="Student is not enrolled in your courses")
    if "student" in roles and current_user.id == student.user_id:
        return
    raise HTTPException(status_code=403, detail="Forbidden")


@router.get("")
def list_students(institution_id: int = None, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    roles = _role_names(current_user)
    q = db.query(Student)
    is_platform_admin = current_user.is_superuser or "super_admin" in roles
    if is_platform_admin:
        if institution_id is not None:
            q = q.filter(Student.institution_id == institution_id)
    elif institution_id is not None and institution_id != current_user.institution_id:
        raise HTTPException(status_code=403, detail="Cross-institution access denied")
    elif roles.intersection({"university_admin", "registrar", "compliance_officer"}):
        q = q.filter(Student.institution_id == current_user.institution_id)
    elif "lecturer" in roles:
        lecturer_query = _lecturer_student_query(db, current_user)
        if lecturer_query is None:
            return []
        q = lecturer_query
    elif "student" in roles:
        q = q.filter(Student.user_id == current_user.id)
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    out = []
    for s in q.all():
        u = db.query(User).filter(User.id == s.user_id).first()
        out.append({"id": s.id, "institution_id": s.institution_id, "user_id": s.user_id,
                    "student_number": s.student_number, "program": s.program, "year_of_study": s.year_of_study,
                    "status": s.status, "attendance_percentage": s.attendance_percentage, "gpa": s.gpa,
                    "full_name": u.full_name if u else None, "email": u.email if u else None})
    return out


@router.get("/{student_id}")
def get_student(student_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    s = db.query(Student).filter(Student.id == student_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Not found")
    _ensure_student_access(db, s, current_user)
    u = db.query(User).filter(User.id == s.user_id).first()
    return {"id": s.id, "institution_id": s.institution_id, "user_id": s.user_id,
            "student_number": s.student_number, "program": s.program, "year_of_study": s.year_of_study,
            "status": s.status, "attendance_percentage": s.attendance_percentage, "gpa": s.gpa,
            "full_name": u.full_name if u else None, "email": u.email if u else None}


@router.post("", status_code=201)
def create_student(payload: StudentCreate, db: Session = Depends(get_db), current_user=Depends(require_roles("university_admin", "registrar", "super_admin"))):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if "student" not in _role_names(user):
        raise HTTPException(status_code=400, detail="A student role is required before creating a student profile")
    if user.institution_id is None:
        raise HTTPException(status_code=400, detail="The student account must belong to an institution")
    if not (current_user.is_superuser or "super_admin" in _role_names(current_user)):
        if current_user.institution_id != user.institution_id:
            raise HTTPException(status_code=403, detail="Cross-institution student creation is not allowed")
    if db.query(Student).filter(Student.user_id == user.id).first():
        raise HTTPException(status_code=409, detail="A student profile already exists for this user")
    if payload.department_id is not None:
        from app.models.department import Department

        department = db.query(Department).filter(Department.id == payload.department_id).first()
        if not department or department.institution_id != user.institution_id:
            raise HTTPException(status_code=400, detail="Department must belong to the student's institution")
    s = Student(**payload.model_dump(), institution_id=user.institution_id)
    db.add(s); db.commit(); db.refresh(s)
    return {"id": s.id}
