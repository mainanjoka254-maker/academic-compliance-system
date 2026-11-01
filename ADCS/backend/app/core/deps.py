from typing import Optional
from fastapi import HTTPException, status, Depends

from app.core.security import get_current_user
from app.models.user import User


def require_roles(*role_names: str):
    def checker(current_user: User = Depends(get_current_user)):
        user_roles = {role.name for role in current_user.roles}
        if not (set(role_names) & user_roles) and not is_super_admin(current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return checker


def get_current_institution_id(current_user: User) -> Optional[int]:
    return current_user.institution_id


def ensure_institution_access(current_user: User, institution_id: Optional[int]):
    if is_super_admin(current_user):
        return
    if institution_id is None or current_user.institution_id != institution_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-institution access denied")


def is_super_admin(user: User) -> bool:
    return user.is_superuser or any(r.name == "super_admin" for r in user.roles)
