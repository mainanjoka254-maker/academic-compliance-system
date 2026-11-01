from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.deps import require_roles, ensure_institution_access, is_super_admin
from app.models.academic import AttendanceRecord, AssessmentRecord, Course, CourseEnrollment
from app.models.student import Lecturer, Student
from app.schemas.academic import AttendanceCreate, AssessmentCreate

router = APIRouter(prefix="/academic", tags=["Attendance & Assessments"])


def _role_names(current_user) -> set[str]:
    return {role.name for role in current_user.roles}


def _ensure_student_record_access(db: Session, student: Student, current_user) -> Lecturer | None:
    ensure_institution_access(current_user, student.institution_id)
    roles = _role_names(current_user)
    if is_super_admin(current_user) or roles.intersection(
        {"university_admin", "registrar", "compliance_officer"}
    ):
        return None
    if "student" in roles and current_user.id == student.user_id:
        return None
    if "lecturer" in roles:
        lecturer = (
            db.query(Lecturer)
            .filter(
                Lecturer.user_id == current_user.id,
                Lecturer.institution_id == student.institution_id,
            )
            .first()
        )
        if lecturer and db.query(CourseEnrollment).join(Course).filter(
            CourseEnrollment.student_id == student.id,
            CourseEnrollment.institution_id == student.institution_id,
            CourseEnrollment.status == "enrolled",
            Course.lecturer_id == lecturer.id,
            Course.institution_id == student.institution_id,
        ).first():
            return lecturer
    raise HTTPException(status_code=403, detail="No access to this student's academic records")


def _ensure_course_assignment(db: Session, current_user, student: Student, course_id: int) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if course.institution_id != student.institution_id:
        raise HTTPException(status_code=403, detail="Course and student must belong to the same institution")
    ensure_institution_access(current_user, course.institution_id)
    roles = _role_names(current_user)
    if not is_super_admin(current_user) and not roles.intersection({"university_admin", "registrar"}):
        lecturer = (
            db.query(Lecturer)
            .filter(
                Lecturer.user_id == current_user.id,
                Lecturer.institution_id == course.institution_id,
            )
            .first()
        )
        if "lecturer" not in roles or not lecturer or course.lecturer_id != lecturer.id:
            raise HTTPException(status_code=403, detail="Course is not assigned to this lecturer")
    enrollment = db.query(CourseEnrollment).filter(
        CourseEnrollment.student_id == student.id,
        CourseEnrollment.institution_id == student.institution_id,
        CourseEnrollment.course_id == course.id,
        CourseEnrollment.status == "enrolled",
    ).first()
    if not enrollment:
        raise HTTPException(status_code=400, detail="Student is not enrolled in this course")
    return course


@router.post("/attendance", status_code=201)
def record_attendance(payload: AttendanceCreate, db: Session = Depends(get_db), current_user=Depends(require_roles("lecturer", "university_admin", "registrar", "super_admin"))):
    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    _ensure_course_assignment(db, current_user, student, payload.course_id)
    rec = AttendanceRecord(institution_id=student.institution_id, student_id=student.id,
                           course_id=payload.course_id, date=payload.date, status=payload.status,
                           recorded_by=current_user.id)
    db.add(rec); db.commit(); db.refresh(rec)
    # update cached attendance percentage
    from app.models.academic import AttendanceRecord as AR
    recs = db.query(AR).filter(
        AR.student_id == student.id,
        AR.institution_id == student.institution_id,
    ).all()
    if recs:
        present = sum(1 for r in recs if r.status in ("present", "late", "excused"))
        student.attendance_percentage = (present / len(recs)) * 100.0
        db.commit()
    return {"id": rec.id}


@router.get("/attendance/{student_id}")
def get_attendance(student_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Not found")
    lecturer = _ensure_student_record_access(db, student, current_user)
    query = db.query(AttendanceRecord).filter(
        AttendanceRecord.student_id == student_id,
        AttendanceRecord.institution_id == student.institution_id,
    )
    if lecturer:
        query = query.join(Course).filter(
            Course.lecturer_id == lecturer.id,
            Course.institution_id == student.institution_id,
        )
    recs = query.all()
    return [{"id": r.id, "course_id": r.course_id, "date": str(r.date), "status": r.status} for r in recs]


@router.post("/assessments", status_code=201)
def record_assessment(payload: AssessmentCreate, db: Session = Depends(get_db), current_user=Depends(require_roles("lecturer", "university_admin", "registrar", "super_admin"))):
    student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    _ensure_course_assignment(db, current_user, student, payload.course_id)
    rec = AssessmentRecord(institution_id=student.institution_id, student_id=student.id,
                           course_id=payload.course_id, title=payload.title,
                           assessment_type=payload.assessment_type, max_score=payload.max_score,
                           score=payload.score, submitted=payload.submitted, due_date=payload.due_date,
                           recorded_by=current_user.id)
    if payload.submitted:
        from datetime import datetime as dt
        rec.submitted_at = dt.utcnow()
    db.add(rec); db.commit(); db.refresh(rec)
    return {"id": rec.id}


@router.get("/assessments/{student_id}")
def get_assessments(student_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Not found")
    lecturer = _ensure_student_record_access(db, student, current_user)
    query = db.query(AssessmentRecord).filter(
        AssessmentRecord.student_id == student_id,
        AssessmentRecord.institution_id == student.institution_id,
    )
    if lecturer:
        query = query.join(Course).filter(
            Course.lecturer_id == lecturer.id,
            Course.institution_id == student.institution_id,
        )
    recs = query.all()
    return [{"id": r.id, "course_id": r.course_id, "title": r.title, "assessment_type": r.assessment_type,
             "max_score": r.max_score, "score": r.score, "submitted": r.submitted, "due_date": str(r.due_date) if r.due_date else None} for r in recs]
