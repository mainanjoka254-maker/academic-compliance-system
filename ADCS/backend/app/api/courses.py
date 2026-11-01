from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.deps import require_roles, ensure_institution_access, is_super_admin
from app.models.academic import Course, CourseEnrollment, AcademicTerm
from app.models.academic_structure import AcademicProgram
from app.models.department import Department
from app.models.student import Lecturer, Student
from app.models.user import User
from app.schemas.academic import CourseCreate, EnrollmentCreate, AcademicTermCreate

router = APIRouter(prefix="/courses", tags=["Courses"])


def _role_names(current_user: User) -> set[str]:
    return {role.name for role in current_user.roles}


def _institution_for_write(current_user: User, requested_id: int | None) -> int:
    if is_super_admin(current_user):
        if requested_id is None:
            raise HTTPException(status_code=422, detail="institution_id is required for platform-level writes")
        return requested_id
    if requested_id is not None and requested_id != current_user.institution_id:
        raise HTTPException(status_code=403, detail="Cross-institution access denied")
    if current_user.institution_id is None:
        raise HTTPException(status_code=403, detail="An institution is required")
    return current_user.institution_id


def _validate_course_references(db: Session, institution_id: int, payload: CourseCreate) -> None:
    references = (
        (Department, payload.department_id, "Department"),
        (AcademicTerm, payload.term_id, "Academic term"),
        (Lecturer, payload.lecturer_id, "Lecturer"),
        (AcademicProgram, payload.program_id, "Academic programme"),
    )
    for model, record_id, label in references:
        if record_id is None:
            continue
        record = db.query(model).filter(model.id == record_id).first()
        if not record or record.institution_id != institution_id:
            raise HTTPException(status_code=400, detail=f"{label} must belong to the selected institution")


@router.get("")
def list_courses(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    roles = _role_names(current_user)
    q = db.query(Course)
    if is_super_admin(current_user):
        pass
    elif roles.intersection({"university_admin", "registrar", "compliance_officer"}):
        q = q.filter(Course.institution_id == current_user.institution_id)
    elif "lecturer" in roles:
        lecturer = db.query(Lecturer).filter(
            Lecturer.user_id == current_user.id,
            Lecturer.institution_id == current_user.institution_id,
        ).first()
        if not lecturer:
            return []
        q = q.filter(
            Course.lecturer_id == lecturer.id,
            Course.institution_id == lecturer.institution_id,
        )
    elif "student" in roles:
        q = q.join(CourseEnrollment).join(Student).filter(
            Student.user_id == current_user.id,
            Student.institution_id == current_user.institution_id,
            Course.institution_id == current_user.institution_id,
            CourseEnrollment.status == "enrolled",
        )
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return [{"id": c.id, "institution_id": c.institution_id, "code": c.code, "name": c.name,
             "credits": c.credits, "department_id": c.department_id, "term_id": c.term_id,
             "lecturer_id": c.lecturer_id, "program_id": c.program_id, "is_active": c.is_active}
            for c in q.distinct().all()]


@router.post("", status_code=201)
def create_course(payload: CourseCreate, db: Session = Depends(get_db), current_user=Depends(require_roles("university_admin", "super_admin"))):
    inst_id = _institution_for_write(current_user, payload.institution_id)
    _validate_course_references(db, inst_id, payload)
    c = Course(institution_id=inst_id, **payload.model_dump(exclude={"institution_id"}))
    db.add(c); db.commit(); db.refresh(c)
    return {"id": c.id, "code": c.code, "name": c.name, "program_id": c.program_id}


@router.get("/{course_id:int}")
def get_course(course_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    c = db.query(Course).filter(Course.id == course_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    ensure_institution_access(current_user, c.institution_id)
    roles = _role_names(current_user)
    if not is_super_admin(current_user) and not roles.intersection(
        {"university_admin", "registrar", "compliance_officer"}
    ):
        if "lecturer" in roles:
            lecturer = db.query(Lecturer).filter(
                Lecturer.user_id == current_user.id,
                Lecturer.institution_id == c.institution_id,
            ).first()
            if not lecturer or c.lecturer_id != lecturer.id:
                raise HTTPException(status_code=403, detail="Course is not assigned to this lecturer")
        elif "student" in roles:
            enrollment = db.query(CourseEnrollment).join(Student).filter(
                Student.user_id == current_user.id,
                Student.institution_id == c.institution_id,
                CourseEnrollment.course_id == c.id,
                CourseEnrollment.status == "enrolled",
            ).first()
            if not enrollment:
                raise HTTPException(status_code=403, detail="Student is not enrolled in this course")
        else:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
    return {
        "id": c.id,
        "code": c.code,
        "name": c.name,
        "credits": c.credits,
        "lecturer_id": c.lecturer_id,
        "program_id": c.program_id,
    }


@router.post("/enroll")
def enroll(payload: EnrollmentCreate, db: Session = Depends(get_db), current_user=Depends(require_roles("university_admin", "registrar", "super_admin"))):
    student = db.query(Student).filter(Student.id == payload.student_id).first()
    course = db.query(Course).filter(Course.id == payload.course_id).first()
    if not student or not course:
        raise HTTPException(status_code=404, detail="Student or course not found")
    ensure_institution_access(current_user, student.institution_id)
    if course.institution_id != student.institution_id:
        raise HTTPException(status_code=403, detail="Cross-institution enrollment not allowed")
    existing = db.query(CourseEnrollment).filter(CourseEnrollment.student_id == student.id, CourseEnrollment.course_id == course.id).first()
    if existing:
        return {"message": "Already enrolled"}
    ce = CourseEnrollment(institution_id=student.institution_id, student_id=student.id, course_id=course.id)
    db.add(ce); db.commit()
    return {"message": "Enrolled"}


@router.get("/terms")
def list_terms(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    q = db.query(AcademicTerm)
    if not is_super_admin(current_user):
        q = q.filter(AcademicTerm.institution_id == current_user.institution_id)
    return [{"id": t.id, "name": t.name, "start_date": str(t.start_date), "end_date": str(t.end_date), "is_current": t.is_current} for t in q.all()]


@router.post("/terms", status_code=201)
def create_term(payload: AcademicTermCreate, db: Session = Depends(get_db), current_user=Depends(require_roles("university_admin", "super_admin"))):
    institution_id = _institution_for_write(current_user, payload.institution_id)
    t = AcademicTerm(institution_id=institution_id, **payload.model_dump(exclude={"institution_id"}))
    db.add(t); db.commit(); db.refresh(t)
    return {"id": t.id, "name": t.name}
