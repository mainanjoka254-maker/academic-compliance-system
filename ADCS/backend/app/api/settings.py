from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user_setting import UserSetting

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/me")
def get_settings(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    setting = db.query(UserSetting).filter(UserSetting.user_id == current_user.id).first()
    if not setting:
        setting = UserSetting(user_id=current_user.id)
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return {
        "theme": setting.theme,
        "language": setting.language,
        "timezone": setting.timezone,
        "email_notifications": setting.email_notifications,
        "in_app_notifications": setting.in_app_notifications,
        "extra": setting.extra or {},
    }


@router.patch("/me")
def update_settings(payload: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    setting = db.query(UserSetting).filter(UserSetting.user_id == current_user.id).first()
    if not setting:
        setting = UserSetting(user_id=current_user.id)
        db.add(setting)
        db.commit()
        db.refresh(setting)
    for field in ("theme", "language", "timezone", "email_notifications", "in_app_notifications"):
        if field in payload:
            setattr(setting, field, payload[field])
    if "extra" in payload and isinstance(payload["extra"], dict):
        setting.extra = {**(setting.extra or {}), **payload["extra"]}
    db.commit()
    return {"message": "Settings updated"}