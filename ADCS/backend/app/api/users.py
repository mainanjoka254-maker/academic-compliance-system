from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, hash_password
from app.core.deps import require_roles, ensure_institution_access, is_super_admin
from app.models.user import User
from app.models.role import Role
from app.models.student import Student, Lecturer
from app.models.department import Department
from app.models.institution import Institution
from app.schemas.user import UserCreate, UserUpdate, RoleAssign

router = APIRouter(prefix="/users", tags=["Users"])


def _roles_list(u):
    return [r.name for r in u.roles]


STAFF_ROLES = {"student", "lecturer", "registrar", "compliance_officer", "university_admin", "super_admin"}


@router.post("", status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db), current_user=Depends(require_roles("university_admin", "super_admin", "registrar"))):
    normalized_email = str(payload.email).strip().lower()
    if db.query(User).filter(User.email == normalized_email).first():
        raise HTTPException(status_code=400, detail="Email exists")
    inst_id = payload.institution_id if payload.institution_id is not None else current_user.institution_id
    ensure_institution_access(current_user, inst_id)
    if inst_id is None or not db.query(Institution.id).filter(
        Institution.id == inst_id,
        Institution.is_active.is_(True),
    ).first():
        raise HTTPException(status_code=400, detail="Select an active institution")
    current_roles = {role.name for role in current_user.roles}
    if payload.role == "super_admin" and not is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Only a platform administrator can assign the super administrator role")
    privileged = {"university_admin", "registrar", "lecturer", "compliance_officer"}
    if payload.role in privileged and not (is_super_admin(current_user) or "university_admin" in current_roles):
        raise HTTPException(status_code=403, detail="Cannot assign privileged role")
    if payload.department_id is not None:
        department = db.query(Department).filter(Department.id == payload.department_id).first()
        if not department or department.institution_id != inst_id:
            raise HTTPException(status_code=400, detail="Department must belong to the selected institution")
    user = User(email=normalized_email, hashed_password=hash_password(payload.password), full_name=payload.full_name,
                institution_id=inst_id, department_id=payload.department_id, phone=payload.phone, is_active=True, is_verified=True)
    db.add(user); db.commit(); db.refresh(user)
    role = db.query(Role).filter(Role.name == payload.role).first()
    if not role:
        role = Role(name=payload.role, description=payload.role, is_system=True); db.add(role); db.commit(); db.refresh(role)
    user.roles.append(role); db.commit()
    if payload.role == "student" and not db.query(Student).filter(Student.user_id == user.id).first():
        db.add(Student(user_id=user.id, institution_id=inst_id, student_number=f"STU{user.id:06d}", department_id=payload.department_id, status="active")); db.commit()
    if payload.role == "lecturer" and not db.query(Lecturer).filter(Lecturer.user_id == user.id).first():
        db.add(Lecturer(user_id=user.id, institution_id=inst_id, staff_number=f"STF{user.id:06d}", department_id=payload.department_id)); db.commit()
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "roles": _roles_list(user)}


@router.get("")
def list_users(institution_id: int = None, db: Session = Depends(get_db), current_user=Depends(require_roles("university_admin", "super_admin", "registrar"))):
    q = db.query(User)
    if not (current_user.is_superuser or any(r.name == "super_admin" for r in current_user.roles)):
        if current_user.institution_id is None:
            raise HTTPException(status_code=403, detail="An institution is required")
        q = q.filter(User.institution_id == current_user.institution_id)
    elif institution_id:
        q = q.filter(User.institution_id == institution_id)
    out = []
    for u in q.all():
        out.append({"id": u.id, "email": u.email, "full_name": u.full_name, "institution_id": u.institution_id,
                    "department_id": u.department_id, "is_active": u.is_active, "is_verified": u.is_verified,
                    "roles": _roles_list(u)})
    return out

@router.get("/me")
def get_me(current_user=Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "full_name": current_user.full_name,
            "phone": current_user.phone, "avatar_url": current_user.avatar_url,
            "institution_id": current_user.institution_id, "department_id": current_user.department_id,
            "roles": _roles_list(current_user), "is_active": current_user.is_active,
            "is_verified": current_user.is_verified, "last_login_at": current_user.last_login_at}


@router.patch("/me")
def update_me(payload: UserUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.phone is not None:
        current_user.phone = payload.phone
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url
    db.commit()
    return {"id": current_user.id, "email": current_user.email, "full_name": current_user.full_name,
            "phone": current_user.phone, "avatar_url": current_user.avatar_url}
def get_user(user_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Not found")
    ensure_institution_access(current_user, u.institution_id)
    if current_user.id != user_id and not is_super_admin(current_user):
        current_roles = {role.name for role in current_user.roles}
        if not current_roles.intersection({"university_admin", "registrar", "compliance_officer"}):
            raise HTTPException(status_code=403, detail="Forbidden")
    return {"id": u.id, "email": u.email, "full_name": u.full_name, "institution_id": u.institution_id,
            "department_id": u.department_id, "is_active": u.is_active, "is_verified": u.is_verified,
            "roles": _roles_list(u)}


@router.patch("/{user_id}")
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), current_user=Depends(require_roles("university_admin", "super_admin"))):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Not found")
    ensure_institution_access(current_user, u.institution_id)
    if payload.department_id is not None:
        department = db.query(Department).filter(Department.id == payload.department_id).first()
        if not department or department.institution_id != u.institution_id:
            raise HTTPException(status_code=400, detail="Department must belong to the user's institution")
    if payload.full_name is not None: u.full_name = payload.full_name
    if payload.phone is not None: u.phone = payload.phone
    if payload.department_id is not None: u.department_id = payload.department_id
    if payload.is_active is not None: u.is_active = payload.is_active
    db.commit()
    return {"id": u.id, "email": u.email, "full_name": u.full_name, "is_active": u.is_active}


@router.post("/assign-role")
def assign_role(payload: RoleAssign, db: Session = Depends(get_db), current_user=Depends(require_roles("university_admin", "super_admin"))):
    u = db.query(User).filter(User.id == payload.user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    ensure_institution_access(current_user, u.institution_id)
    if payload.institution_id is not None and payload.institution_id != u.institution_id:
        raise HTTPException(status_code=403, detail="Role assignment institution must match the user's institution")
    current_roles = {role.name for role in current_user.roles}
    if payload.role_name == "super_admin" and not is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Only a platform administrator can assign the super administrator role")
    privileged = {"university_admin", "registrar", "lecturer", "compliance_officer"}
    if payload.role_name in privileged and not (is_super_admin(current_user) or "university_admin" in current_roles):
        raise HTTPException(status_code=403, detail="Cannot assign privileged role")
    role = db.query(Role).filter(Role.name == payload.role_name).first()
    if not role:
        role = Role(name=payload.role_name, description=payload.role_name, is_system=True); db.add(role); db.commit(); db.refresh(role)
    if role not in u.roles:
        u.roles.append(role); db.commit()
    return {"user_id": u.id, "roles": [r.name for r in u.roles]}
