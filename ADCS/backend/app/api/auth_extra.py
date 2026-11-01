from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import secrets

from app.core.database import get_db
from app.core.security import hash_password, create_access_token, decode_token
from app.core.config import settings
from app.core.security import get_current_user
from app.models.user import User
from app.models.notification import PasswordResetToken
from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest, RefreshTokenRequest
from app.services.email_service import send_email
from app.services.notification_service import create_notification
from app.services.audit_service import log_action
from app.core.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/forgot-password")
@limiter.limit(settings.RATE_LIMIT_REGISTER)
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    normalized_email = str(payload.email).strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if user:
        token = secrets.token_urlsafe(32)
        pr = PasswordResetToken(user_id=user.id, token=token, expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES))
        db.add(pr); db.commit()
        reset_link = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/reset-password?token={token}"
        if send_email(normalized_email, "ADCS Password Reset", f"Reset your password: {reset_link}"):
            create_notification(
                db,
                user.id,
                "Password reset requested",
                "A password reset link was sent.",
                type_="password_reset",
                institution_id=user.institution_id,
            )
        else:
            log_action(
                db,
                "password_reset_email_delivery_failed",
                user_id=user.id,
                institution_id=user.institution_id,
                success=False,
            )
    return {"message": "If the email exists, a reset link has been sent."}


@router.post("/reset-password")
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def reset_password(payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    pr = db.query(PasswordResetToken).filter(PasswordResetToken.token == payload.token, PasswordResetToken.used == False).first()
    if not pr:
        raise HTTPException(status_code=400, detail="Invalid or used token")
    if pr.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token expired")
    user = db.query(User).filter(User.id == pr.user_id).first()
    user.hashed_password = hash_password(payload.new_password)
    user.auth_provider = "password+google" if user.google_sub else "password"
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used.is_(False),
    ).update({"used": True}, synchronize_session=False)
    db.commit()
    log_action(db, "password_reset", user_id=user.id, institution_id=user.institution_id)
    return {"message": "Password reset successful."}


@router.post("/refresh")
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    data = decode_token(payload.refresh_token)
    if data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user = db.query(User).filter(User.id == int(data["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    roles = [r.name for r in user.roles]
    access = create_access_token({"sub": str(user.id), "roles": roles, "institution_id": user.institution_id})
    return {"access_token": access, "token_type": "bearer"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "full_name": current_user.full_name,
            "institution_id": current_user.institution_id, "roles": [r.name for r in current_user.roles],
            "is_active": current_user.is_active, "is_verified": current_user.is_verified}
