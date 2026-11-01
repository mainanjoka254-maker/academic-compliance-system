from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import ensure_institution_access, is_super_admin, require_roles
from app.models.academic_structure import AcademicProgram, Faculty
from app.models.department import Department
from app.models.institution import Institution
from app.models.user import User
from app.schemas.academic_structure import (
    AcademicProgramCreate,
    DepartmentCreate,
    DepartmentFacultyUpdate,
    FacultyCreate,
)

router = APIRouter(prefix="/academic-structure", tags=["Academic Structure"])
MANAGER_ROLES = ("university_admin", "registrar", "super_admin")


def _institution_scope(db: Session, current_user: User, requested_id: int | None) -> int:
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


def _validate_faculty(db: Session, institution_id: int, faculty_id: int | None) -> Faculty | None:
    if faculty_id is None:
        return None
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if not faculty or faculty.institution_id != institution_id:
        raise HTTPException(status_code=400, detail="Faculty must belong to this institution")
    return faculty


def _validate_department(db: Session, institution_id: int, department_id: int | None) -> Department | None:
    if department_id is None:
        return None
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department or department.institution_id != institution_id:
        raise HTTPException(status_code=400, detail="Department must belong to this institution")
    return department


@router.get("/faculties")
def list_faculties(
    institution_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    scope_id = _institution_scope(db, current_user, institution_id)
    faculties = db.query(Faculty).filter(
        Faculty.institution_id == scope_id,
        Faculty.is_active.is_(True),
    ).order_by(Faculty.name).all()
    return [{"id": row.id, "institution_id": row.institution_id, "name": row.name, "code": row.code}
            for row in faculties]


@router.post("/faculties", status_code=201)
def create_faculty(
    payload: FacultyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    institution_id = _institution_scope(db, current_user, payload.institution_id)
    faculty = Faculty(institution_id=institution_id, name=payload.name.strip(), code=payload.code.strip())
    db.add(faculty)
    try:
        db.commit()
        db.refresh(faculty)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Faculty code already exists in this institution") from exc
    return {"id": faculty.id, "institution_id": faculty.institution_id, "name": faculty.name, "code": faculty.code}


@router.get("/departments")
def list_departments(
    institution_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    scope_id = _institution_scope(db, current_user, institution_id)
    departments = db.query(Department).filter(
        Department.institution_id == scope_id,
        Department.is_active.is_(True),
    ).order_by(Department.name).all()
    return [
        {
            "id": row.id,
            "institution_id": row.institution_id,
            "faculty_id": row.faculty_id,
            "name": row.name,
            "code": row.code,
            "description": row.description,
        }
        for row in departments
    ]


@router.post("/departments", status_code=201)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    institution_id = _institution_scope(db, current_user, payload.institution_id)
    _validate_faculty(db, institution_id, payload.faculty_id)
    department = Department(
        institution_id=institution_id,
        faculty_id=payload.faculty_id,
        name=payload.name.strip(),
        code=payload.code.strip(),
        description=payload.description,
    )
    db.add(department)
    try:
        db.commit()
        db.refresh(department)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Department could not be created due to a conflicting record") from exc
    return {
        "id": department.id,
        "institution_id": department.institution_id,
        "faculty_id": department.faculty_id,
        "name": department.name,
        "code": department.code,
        "description": department.description,
    }


@router.patch("/departments/{department_id}/faculty")
def assign_department_faculty(
    department_id: int,
    payload: DepartmentFacultyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("university_admin", "super_admin")),
):
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    ensure_institution_access(current_user, department.institution_id)
    _validate_faculty(db, department.institution_id, payload.faculty_id)
    department.faculty_id = payload.faculty_id
    db.commit()
    return {"id": department.id, "faculty_id": department.faculty_id}


@router.get("/programmes")
def list_programmes(
    institution_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    scope_id = _institution_scope(db, current_user, institution_id)
    programs = db.query(AcademicProgram).filter(
        AcademicProgram.institution_id == scope_id,
        AcademicProgram.is_active.is_(True),
    ).order_by(AcademicProgram.name).all()
    return [
        {
            "id": row.id,
            "institution_id": row.institution_id,
            "faculty_id": row.faculty_id,
            "department_id": row.department_id,
            "name": row.name,
            "code": row.code,
            "award_level": row.award_level,
        }
        for row in programs
    ]


@router.post("/programmes", status_code=201)
def create_programme(
    payload: AcademicProgramCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGER_ROLES)),
):
    institution_id = _institution_scope(db, current_user, payload.institution_id)
    _validate_faculty(db, institution_id, payload.faculty_id)
    department = _validate_department(db, institution_id, payload.department_id)
    if department and payload.faculty_id and department.faculty_id not in (None, payload.faculty_id):
        raise HTTPException(status_code=400, detail="Department does not belong to the selected faculty")
    program = AcademicProgram(
        institution_id=institution_id,
        faculty_id=payload.faculty_id or (department.faculty_id if department else None),
        department_id=payload.department_id,
        name=payload.name.strip(),
        code=payload.code.strip(),
        award_level=payload.award_level,
    )
    db.add(program)
    try:
        db.commit()
        db.refresh(program)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Programme code already exists in this institution") from exc
    return {
        "id": program.id,
        "institution_id": program.institution_id,
        "faculty_id": program.faculty_id,
        "department_id": program.department_id,
        "name": program.name,
        "code": program.code,
        "award_level": program.award_level,
    }
