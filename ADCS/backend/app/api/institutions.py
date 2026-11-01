from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, hash_password
from app.core.deps import require_roles, ensure_institution_access, is_super_admin
from app.models.institution import Institution
from app.models.department import Department
from app.models.role import Role
from app.models.user import User
from app.schemas.user import (
    InstitutionAdministratorCreate,
    InstitutionAdministratorStatus,
    InstitutionCreate,
    InstitutionOut,
    InstitutionUpdate,
)
from app.schemas.academic import DepartmentCreate, DepartmentOut
from app.services.audit_service import log_action

router = APIRouter(prefix="/institutions", tags=["Institutions"])


@router.post("", status_code=201, response_model=InstitutionOut)
def create_institution(
    payload: InstitutionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("super_admin")),
):
    inst = Institution(**payload.model_dump())
    db.add(inst)
    try:
        db.flush()
        db.commit()
        db.refresh(inst)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An institution with that name or code already exists",
        ) from exc
    log_action(
        db,
        "institution.created",
        user_id=current_user.id,
        resource_type="institution",
        resource_id=inst.id,
        ip_address=request.client.host if request.client else None,
    )
    return inst


@router.get("", response_model=list[InstitutionOut])
def list_institutions(db: Session = Depends(get_db), current_user=Depends(require_roles("super_admin", "university_admin"))):
    q = db.query(Institution)
    if not (current_user.is_superuser or any(r.name == "super_admin" for r in current_user.roles)):
        if current_user.institution_id is None:
            raise HTTPException(status_code=403, detail="An institution is required")
        q = q.filter(Institution.id == current_user.institution_id)
    return q.all()


@router.get("/registration-options")
def registration_options(db: Session = Depends(get_db)):
    institutions = (
        db.query(Institution.id, Institution.name)
        .filter(Institution.is_active.is_(True))
        .order_by(Institution.name)
        .all()
    )
    return [{"id": institution_id, "name": name} for institution_id, name in institutions]


@router.patch("/{institution_id}", response_model=InstitutionOut)
def update_institution(
    institution_id: int,
    payload: InstitutionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("super_admin")),
):
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one institution field must be provided")
    for field, value in changes.items():
        setattr(inst, field, value)
    try:
        db.commit()
        db.refresh(inst)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An institution with that name or code already exists",
        ) from exc
    log_action(
        db,
        "institution.updated",
        user_id=current_user.id,
        resource_type="institution",
        resource_id=inst.id,
        ip_address=request.client.host if request.client else None,
    )
    return inst


@router.get("/{institution_id}")
def get_institution(institution_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    ensure_institution_access(current_user, institution_id)
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Not found")
    return inst


@router.patch("/{institution_id}/activate")
def toggle_institution(institution_id: int, is_active: bool, db: Session = Depends(get_db), current_user=Depends(require_roles("super_admin"))):
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Not found")
    inst.is_active = is_active
    db.commit()
    log_action(
        db,
        "institution.activated" if is_active else "institution.deactivated",
        user_id=current_user.id,
        resource_type="institution",
        resource_id=inst.id,
    )
    return {"id": inst.id, "is_active": inst.is_active}


@router.get("/{institution_id}/administrators")
def list_institution_administrators(
    institution_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("super_admin")),
):
    institution = db.query(Institution).filter(Institution.id == institution_id).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    admins = (
        db.query(User)
        .filter(
            User.institution_id == institution_id,
            User.roles.any(Role.name == "university_admin"),
        )
        .order_by(User.full_name)
        .all()
    )
    return [
        {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
        }
        for user in admins
    ]


@router.post("/{institution_id}/administrators", status_code=201)
def create_institution_administrator(
    institution_id: int,
    payload: InstitutionAdministratorCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("super_admin")),
):
    institution = db.query(Institution).filter(
        Institution.id == institution_id,
        Institution.is_active.is_(True),
    ).first()
    if not institution:
        raise HTTPException(status_code=404, detail="Active institution not found")
    email = str(payload.email).strip().lower()
    if db.query(User.id).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    role = db.query(Role).filter(Role.name == "university_admin").first()
    if role is None:
        role = Role(name="university_admin", description="Institution administrator", is_system=True)
        db.add(role)
        db.flush()
    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        phone=payload.phone,
        institution_id=institution_id,
        auth_provider="password",
        is_active=True,
        is_verified=True,
        approval_status="approved",
    )
    user.roles.append(role)
    db.add(user)
    try:
        db.flush()
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Administrator account could not be created") from exc
    log_action(
        db,
        "institution.administrator_created",
        user_id=current_user.id,
        institution_id=institution_id,
        resource_type="user",
        resource_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "institution_id": user.institution_id,
        "is_active": user.is_active,
        "roles": ["university_admin"],
    }


@router.patch("/{institution_id}/administrators/{user_id}")
def update_institution_administrator(
    institution_id: int,
    user_id: int,
    payload: InstitutionAdministratorStatus,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("super_admin")),
):
    user = db.query(User).filter(
        User.id == user_id,
        User.institution_id == institution_id,
        User.roles.any(Role.name == "university_admin"),
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Institution administrator not found")
    if user.is_superuser or is_super_admin(user):
        raise HTTPException(status_code=403, detail="Platform administrator accounts cannot be managed as institution administrators")
    user.is_active = payload.is_active
    db.commit()
    log_action(
        db,
        "institution.administrator.activated" if payload.is_active else "institution.administrator.deactivated",
        user_id=current_user.id,
        institution_id=institution_id,
        resource_type="user",
        resource_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    return {"id": user.id, "is_active": user.is_active}


@router.post("/{institution_id}/departments", status_code=201)
def create_department(institution_id: int, payload: DepartmentCreate, db: Session = Depends(get_db), current_user=Depends(require_roles("university_admin", "super_admin"))):
    ensure_institution_access(current_user, institution_id)
    dept = Department(institution_id=institution_id, **payload.model_dump())
    db.add(dept); db.commit(); db.refresh(dept)
    return dept


@router.get("/{institution_id}/departments")
def list_departments(institution_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    ensure_institution_access(current_user, institution_id)
    return db.query(Department).filter(Department.institution_id == institution_id).all()
