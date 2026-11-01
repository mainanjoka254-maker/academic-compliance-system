import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import ensure_institution_access, is_super_admin, require_roles
from app.core.security import get_current_user, hash_password
from app.models.academic import AssessmentRecord, Course
from app.models.academic_structure import AcademicProgram
from app.models.document import AcademicDocument
from app.models.institution import Institution
from app.models.notification import AuditLog
from app.models.role import Role
from app.models.student import Lecturer, Student
from app.models.user import User
from app.services.audit_service import log_action
from app.schemas.lecturer import (
    LecturerCreate,
    LecturerUpdate,
    ProgramAssignmentUpdate,
    TeachingAssignmentUpdate,
)

router = APIRouter(prefix="/lecturers", tags=["Lecturer Management"])
MANAGER_ROLES = {"university_admin", "registrar"}


def _role_names(user: User) -> set[str]:
    return {role.name for role in user.roles}


def _resolve_institution(db: Session, current_user: User, requested_id: int | None) -> int:
    if is_super_admin(current_user):
        institution_id = requested_id
    else:
        institution_id = current_user.institution_id
        if requested_id is not None and requested_id != institution_id:
            raise HTTPException(status_code=403, detail="Cross-institution access denied")
    if institution_id is None:
        raise HTTPException(status_code=422, detail="institution_id is required")
    if not db.query(Institution.id).filter(
        Institution.id == institution_id,
        Institution.is_active.is_(True),
    ).first():
        raise HTTPException(status_code=404, detail="Active institution not found")
    return institution_id


def _lecturer_for_access(db: Session, lecturer_id: int, current_user: User) -> Lecturer:
    lecturer = db.query(Lecturer).filter(Lecturer.id == lecturer_id).first()
    if not lecturer:
        raise HTTPException(status_code=404, detail="Lecturer not found")
    if not is_super_admin(current_user):
        ensure_institution_access(current_user, lecturer.institution_id)
        if current_user.id != lecturer.user_id and not _role_names(current_user).intersection(MANAGER_ROLES):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
    return lecturer


def _lecturer_payload(db: Session, lecturer: Lecturer) -> dict:
    user = db.query(User).filter(User.id == lecturer.user_id).first()
    courses = db.query(Course).filter(
        Course.lecturer_id == lecturer.id,
        Course.institution_id == lecturer.institution_id,
    ).order_by(Course.code).all()
    return {
        "id": lecturer.id,
        "user_id": lecturer.user_id,
        "institution_id": lecturer.institution_id,
        "department_id": lecturer.department_id,
        "staff_number": lecturer.staff_number,
        "title": lecturer.title,
        "specialization": lecturer.specialization,
        "full_name": user.full_name if user else None,
        "email": user.email if user else None,
        "phone": user.phone if user else None,
        "is_active": user.is_active if user else False,
        "courses": [{"id": course.id, "code": course.code, "name": course.name} for course in courses],
        "programs": [
            {"id": program.id, "code": program.code, "name": program.name}
            for program in sorted(lecturer.programs, key=lambda item: item.code)
        ],
    }


def _submission_metrics(db: Session, lecturer: Lecturer) -> dict:
    courses = db.query(Course).filter(
        Course.lecturer_id == lecturer.id,
        Course.institution_id == lecturer.institution_id,
    ).all()
    course_ids = [course.id for course in courses]
    submissions = []
    if course_ids:
        submissions = db.query(AcademicDocument).filter(
            AcademicDocument.course_id.in_(course_ids),
            AcademicDocument.institution_id == lecturer.institution_id,
            AcademicDocument.purpose == "lecturer_submission",
        ).order_by(AcademicDocument.created_at.desc()).all()
    reported_course_ids = {document.course_id for document in submissions}
    return {
        "assigned_courses": len(courses),
        "course_submissions": len(submissions),
        "pending_verification": sum(document.status == "pending" for document in submissions),
        "rejected_submissions": sum(document.status == "rejected" for document in submissions),
        "courses_without_submission": [
            {"id": course.id, "code": course.code, "name": course.name}
            for course in courses if course.id not in reported_course_ids
        ],
        "submission_records": [
            {
                "id": document.id,
                "course_id": document.course_id,
                "filename": document.original_filename,
                "status": document.status,
                "created_at": document.created_at,
                "reviewed_at": document.reviewed_at,
            }
            for document in submissions
        ],
    }


@router.get("")
def list_lecturers(
    institution_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("university_admin", "registrar", "super_admin")),
):
    scope_id = _resolve_institution(db, current_user, institution_id)
    rows = db.query(Lecturer).filter(
        Lecturer.institution_id == scope_id,
    ).order_by(Lecturer.staff_number).all()
    return [_lecturer_payload(db, lecturer) for lecturer in rows]


@router.get("/registration-requests")
def list_lecturer_registration_requests(
    institution_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("university_admin", "registrar", "super_admin")),
):
    query = db.query(User).filter(
        User.requested_role == "lecturer",
        User.approval_status == "pending",
    )
    if is_super_admin(current_user) and institution_id is None:
        query = query.join(Institution, Institution.id == User.institution_id).filter(
            Institution.is_active.is_(True),
        )
    else:
        scope_id = _resolve_institution(db, current_user, institution_id)
        query = query.filter(User.institution_id == scope_id)
    requests = query.order_by(User.created_at).all()
    return [
        {
            "user_id": user.id,
            "institution_id": user.institution_id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "staff_number": user.requested_staff_number,
            "is_verified": user.is_verified,
        }
        for user in requests
    ]


@router.post("/{user_id:int}/registration-request/approve")
def approve_lecturer_registration(
    user_id: int,
    request: Request,
    institution_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("university_admin", "registrar", "super_admin")),
):
    user = db.query(User).filter(
        User.id == user_id,
        User.requested_role == "lecturer",
        User.approval_status == "pending",
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Pending lecturer registration not found")
    scope_id = _resolve_institution(db, current_user, institution_id or user.institution_id)
    if scope_id != user.institution_id:
        raise HTTPException(status_code=403, detail="Cross-institution access denied")
    if not user.is_verified:
        raise HTTPException(status_code=409, detail="The applicant must verify their email before approval")
    if not user.requested_staff_number:
        raise HTTPException(status_code=409, detail="The lecturer request is missing its staff number")
    if db.query(Lecturer.id).filter(
        Lecturer.institution_id == scope_id,
        Lecturer.staff_number == user.requested_staff_number,
    ).first():
        raise HTTPException(status_code=409, detail="Staff number is already assigned in this institution")

    role = db.query(Role).filter(Role.name == "lecturer").first()
    if role is None:
        role = Role(name="lecturer", description="Lecturer", is_system=True)
        db.add(role)
        db.flush()
    lecturer = Lecturer(
        institution_id=scope_id,
        user_id=user.id,
        staff_number=user.requested_staff_number,
    )
    user.roles.append(role)
    user.requested_role = None
    user.approval_status = "approved"
    user.is_active = True
    db.add(lecturer)
    try:
        db.flush()
        db.commit()
        db.refresh(lecturer)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Lecturer registration conflicts with an existing account or staff number",
        ) from exc
    log_action(
        db,
        "lecturer.registration_approved",
        user_id=current_user.id,
        institution_id=scope_id,
        resource_type="lecturer",
        resource_id=lecturer.id,
        ip_address=request.client.host if request.client else None,
    )
    return _lecturer_payload(db, lecturer)


@router.post("/{user_id:int}/registration-request/reject")
def reject_lecturer_registration(
    user_id: int,
    request: Request,
    institution_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("university_admin", "registrar", "super_admin")),
):
    user = db.query(User).filter(
        User.id == user_id,
        User.requested_role == "lecturer",
        User.approval_status == "pending",
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Pending lecturer registration not found")
    scope_id = _resolve_institution(db, current_user, institution_id or user.institution_id)
    if scope_id != user.institution_id:
        raise HTTPException(status_code=403, detail="Cross-institution access denied")
    user.approval_status = "rejected"
    user.is_active = False
    db.commit()
    log_action(
        db,
        "lecturer.registration_rejected",
        user_id=current_user.id,
        institution_id=scope_id,
        resource_type="user",
        resource_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    return {"user_id": user.id, "approval_status": user.approval_status}


@router.post("", status_code=201)
def create_lecturer(
    payload: LecturerCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("university_admin", "registrar", "super_admin")),
):
    institution_id = _resolve_institution(db, current_user, payload.institution_id)
    email = str(payload.email).strip().lower()
    if db.query(User.id).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    if db.query(Lecturer.id).filter(
        Lecturer.institution_id == institution_id,
        Lecturer.staff_number == payload.staff_number,
    ).first():
        raise HTTPException(status_code=409, detail="Staff number already exists in this institution")
    if payload.department_id is not None:
        from app.models.department import Department

        department = db.query(Department).filter(Department.id == payload.department_id).first()
        if not department or department.institution_id != institution_id:
            raise HTTPException(status_code=400, detail="Department must belong to this institution")

    role = db.query(Role).filter(Role.name == "lecturer").first()
    if role is None:
        role = Role(name="lecturer", description="Lecturer", is_system=True)
        db.add(role)
        db.flush()
    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        institution_id=institution_id,
        department_id=payload.department_id,
        is_active=True,
        is_verified=True,
    )
    user.roles.append(role)
    db.add(user)
    try:
        db.flush()
        lecturer = Lecturer(
            institution_id=institution_id,
            user_id=user.id,
            department_id=payload.department_id,
            staff_number=payload.staff_number,
            title=payload.title,
            specialization=payload.specialization,
        )
        db.add(lecturer)
        db.flush()
        db.add(AuditLog(
            institution_id=institution_id,
            user_id=current_user.id,
            action="lecturer.created",
            resource_type="lecturer",
            resource_id=lecturer.id,
            ip_address=request.client.host if request.client else None,
        ))
        db.commit()
        db.refresh(lecturer)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Lecturer account could not be created due to a conflicting record") from exc
    return _lecturer_payload(db, lecturer)


@router.get("/{lecturer_id:int}")
def get_lecturer(
    lecturer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lecturer = _lecturer_for_access(db, lecturer_id, current_user)
    return _lecturer_payload(db, lecturer)


@router.patch("/{lecturer_id:int}")
def update_lecturer(
    lecturer_id: int,
    payload: LecturerUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("university_admin", "super_admin")),
):
    lecturer = _lecturer_for_access(db, lecturer_id, current_user)
    user = db.query(User).filter(User.id == lecturer.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Lecturer account not found")
    changes = payload.model_dump(exclude_unset=True)
    if "department_id" in changes:
        if payload.department_id is not None:
            from app.models.department import Department

            department = db.query(Department).filter(Department.id == payload.department_id).first()
            if not department or department.institution_id != lecturer.institution_id:
                raise HTTPException(status_code=400, detail="Department must belong to this institution")
        lecturer.department_id = payload.department_id
        user.department_id = payload.department_id
    if "full_name" in changes:
        user.full_name = payload.full_name
    if "phone" in changes:
        user.phone = payload.phone
    if "is_active" in changes:
        user.is_active = payload.is_active
        user.deactivated_at = None if payload.is_active else datetime.now(timezone.utc).replace(tzinfo=None)
    if "title" in changes:
        lecturer.title = payload.title
    if "specialization" in changes:
        lecturer.specialization = payload.specialization
    db.add(AuditLog(
        institution_id=lecturer.institution_id,
        user_id=current_user.id,
        action="lecturer.updated",
        resource_type="lecturer",
        resource_id=lecturer.id,
        ip_address=request.client.host if request.client else None,
    ))
    db.commit()
    return _lecturer_payload(db, lecturer)


@router.put("/{lecturer_id:int}/courses")
def assign_courses(
    lecturer_id: int,
    payload: TeachingAssignmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("university_admin", "registrar", "super_admin")),
):
    lecturer = _lecturer_for_access(db, lecturer_id, current_user)
    if len(set(payload.course_ids)) != len(payload.course_ids):
        raise HTTPException(status_code=422, detail="Course IDs must be unique")
    courses = db.query(Course).filter(Course.id.in_(payload.course_ids)).all() if payload.course_ids else []
    if len(courses) != len(payload.course_ids):
        raise HTTPException(status_code=404, detail="One or more courses were not found")
    for course in courses:
        if course.institution_id != lecturer.institution_id:
            raise HTTPException(status_code=403, detail="Courses must belong to the lecturer's institution")
        if course.lecturer_id not in (None, lecturer.id):
            raise HTTPException(status_code=409, detail=f"Course {course.code} is assigned to another lecturer")

    existing = db.query(Course).filter(
        Course.lecturer_id == lecturer.id,
        Course.institution_id == lecturer.institution_id,
    ).all()
    requested_ids = set(payload.course_ids)
    for course in existing:
        if course.id not in requested_ids:
            course.lecturer_id = None
    for course in courses:
        course.lecturer_id = lecturer.id
    db.add(AuditLog(
        institution_id=lecturer.institution_id,
        user_id=current_user.id,
        action="lecturer.courses_assigned",
        resource_type="lecturer",
        resource_id=lecturer.id,
        ip_address=request.client.host if request.client else None,
        details=f"course_ids={sorted(requested_ids)}",
    ))
    db.commit()
    return _lecturer_payload(db, lecturer)


@router.put("/{lecturer_id:int}/programs")
def assign_programs(
    lecturer_id: int,
    payload: ProgramAssignmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("university_admin", "registrar", "super_admin")),
):
    lecturer = _lecturer_for_access(db, lecturer_id, current_user)
    if len(set(payload.program_ids)) != len(payload.program_ids):
        raise HTTPException(status_code=422, detail="Programme IDs must be unique")
    programs = db.query(AcademicProgram).filter(
        AcademicProgram.id.in_(payload.program_ids),
        AcademicProgram.is_active.is_(True),
    ).all() if payload.program_ids else []
    if len(programs) != len(payload.program_ids):
        raise HTTPException(status_code=404, detail="One or more programmes were not found or are inactive")
    if any(program.institution_id != lecturer.institution_id for program in programs):
        raise HTTPException(status_code=403, detail="Programmes must belong to the lecturer's institution")

    lecturer.programs = programs
    db.add(AuditLog(
        institution_id=lecturer.institution_id,
        user_id=current_user.id,
        action="lecturer.programs_assigned",
        resource_type="lecturer",
        resource_id=lecturer.id,
        ip_address=request.client.host if request.client else None,
        details=f"program_ids={sorted(payload.program_ids)}",
    ))
    db.commit()
    return _lecturer_payload(db, lecturer)


@router.get("/{lecturer_id:int}/compliance")
def lecturer_compliance_report(
    lecturer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lecturer = _lecturer_for_access(db, lecturer_id, current_user)
    metrics = _submission_metrics(db, lecturer)
    course_ids = [course["id"] for course in _lecturer_payload(db, lecturer)["courses"]]
    metrics["assessments_without_scores"] = db.query(AssessmentRecord.id).filter(
        AssessmentRecord.course_id.in_(course_ids),
        AssessmentRecord.institution_id == lecturer.institution_id,
        AssessmentRecord.score.is_(None),
    ).count() if course_ids else 0
    metrics["compliance_status"] = (
        "attention_required"
        if metrics["courses_without_submission"] or metrics["rejected_submissions"]
        else "complete"
    )
    metrics["explanation"] = (
        "Course compliance is based on uploaded lecturer submissions and their verification status. "
        "No submission deadlines are configured in the current data model."
    )
    return metrics


@router.get("/{lecturer_id:int}/report.csv")
def download_lecturer_report(
    lecturer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("university_admin", "registrar", "super_admin")),
):
    lecturer = _lecturer_for_access(db, lecturer_id, current_user)
    metrics = _submission_metrics(db, lecturer)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["lecturer_id", lecturer.id])
    writer.writerow(["staff_number", lecturer.staff_number])
    writer.writerow(["institution_id", lecturer.institution_id])
    writer.writerow(["assigned_courses", metrics["assigned_courses"]])
    writer.writerow(["course_submissions", metrics["course_submissions"]])
    writer.writerow(["pending_verification", metrics["pending_verification"]])
    writer.writerow(["rejected_submissions", metrics["rejected_submissions"]])
    writer.writerow(["course_without_submission_id", "course_code", "course_name"])
    writer.writerows(
        [course["id"], course["code"], course["name"]]
        for course in metrics["courses_without_submission"]
    )
    filename = f"lecturer-{lecturer.id}-compliance.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
