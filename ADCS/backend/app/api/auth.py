from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import secrets

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.config import settings
from app.models.user import User
from app.models.role import Role
from app.models.notification import EmailVerificationToken, PasswordResetToken
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    OTPVerifyRequest,
    ResendOTPRequest,
)
from app.services.email_service import send_email
from app.services.notification_service import create_notification
from app.services.audit_service import log_action
from app.core.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_or_create_role(db, name):
    r = db.query(Role).filter(Role.name == name).first()
    if not r:
        r = Role(name=name, description=name, is_system=True)
        db.add(r); db.commit(); db.refresh(r)
    return r


@router.post("/register", status_code=201)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    requested_role = payload.role_requested or "student"
    if requested_role not in {"student", "lecturer"}:
        raise HTTPException(status_code=403, detail="Privileged roles require institutional approval")
    if requested_role == "lecturer" and not payload.staff_number:
        raise HTTPException(status_code=422, detail="A staff number is required for lecturer registration")
    if requested_role == "student" and payload.staff_number is not None:
        raise HTTPException(status_code=422, detail="Staff number is only valid for lecturer registration")
    normalized_email = str(payload.email).strip().lower()
    if db.query(User).filter(User.email == normalized_email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    from app.models.institution import Institution
    inst = db.query(Institution).filter(Institution.id == payload.institution_id, Institution.is_active == True).first()
    if not inst:
        raise HTTPException(status_code=400, detail="Invalid or inactive institution")
    lecturer_request = requested_role == "lecturer"
    if lecturer_request:
        from app.models.student import Lecturer

        duplicate_staff_number = db.query(Lecturer.id).filter(
            Lecturer.institution_id == payload.institution_id,
            Lecturer.staff_number == payload.staff_number,
        ).first()
        pending_staff_number = db.query(User.id).filter(
            User.institution_id == payload.institution_id,
            User.requested_staff_number == payload.staff_number,
            User.approval_status == "pending",
        ).first()
        if duplicate_staff_number or pending_staff_number:
            raise HTTPException(status_code=409, detail="Staff number is already registered or awaiting approval")
    user = User(
        email=normalized_email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        institution_id=payload.institution_id,
        auth_provider="password",
        requested_role="lecturer" if lecturer_request else None,
        requested_staff_number=payload.staff_number if lecturer_request else None,
        approval_status="pending" if lecturer_request else "approved",
        is_active=False,
        is_verified=False,
    )
    db.add(user); db.commit(); db.refresh(user)
    if not lecturer_request:
        role = _get_or_create_role(db, "student")
        user.roles.append(role); db.commit()
        from app.models.student import Student
        sp = Student(user_id=user.id, institution_id=payload.institution_id, student_number=f"STU{user.id:06d}", status="active")
        db.add(sp); db.commit()
    otp = f"{secrets.randbelow(1_000_000):06d}"
    tok = EmailVerificationToken(user_id=user.id, token=otp, expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.EMAIL_OTP_EXPIRE_MINUTES))
    db.add(tok); db.commit()
    if not send_email(normalized_email, "ADCS Email Verification", f"Your verification code is: {otp}"):
        log_action(
            db,
            "verification_email_delivery_failed",
            user_id=user.id,
            institution_id=payload.institution_id,
            success=False,
        )
        raise HTTPException(
            status_code=503,
            detail="Your account was created, but verification email delivery failed. Configure SMTP and request a new code.",
        )
    create_notification(
        db,
        user.id,
        "Verify your account",
        "A verification code was sent to your email address.",
        type_="account_verification",
        institution_id=payload.institution_id,
    )
    log_action(db, "user_registered", user_id=user.id, institution_id=payload.institution_id)
    message = (
        "Lecturer request submitted. Verify your email; institutional approval is also required."
        if lecturer_request
        else "Registration successful. Please verify your email with the OTP sent."
    )
    return {"message": message, "user_id": user.id}


@router.post("/resend-otp")
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def resend_otp(payload: ResendOTPRequest, request: Request, db: Session = Depends(get_db)):
    normalized_email = str(payload.email).strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or user.is_verified:
        return {"message": "If the account needs verification, a new code has been sent."}
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id,
        EmailVerificationToken.used.is_(False),
    ).update({"used": True}, synchronize_session=False)
    otp = f"{secrets.randbelow(1_000_000):06d}"
    token = EmailVerificationToken(
        user_id=user.id,
        token=otp,
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=settings.EMAIL_OTP_EXPIRE_MINUTES),
    )
    db.add(token)
    db.commit()
    if not send_email(normalized_email, "ADCS Email Verification", f"Your verification code is: {otp}"):
        log_action(
            db,
            "verification_email_delivery_failed",
            user_id=user.id,
            institution_id=user.institution_id,
            success=False,
        )
        raise HTTPException(
            status_code=503,
            detail="Verification email delivery failed. Contact your institution administrator.",
        )
    return {"message": "If the account needs verification, a new code has been sent."}


@router.post("/verify-otp")
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def verify_otp(payload: OTPVerifyRequest, request: Request, db: Session = Depends(get_db)):
    normalized_email = str(payload.email).strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    tok = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id, EmailVerificationToken.token == payload.otp,
        EmailVerificationToken.used == False).first()
    if not tok:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    if tok.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="OTP expired")
    tok.used = True
    user.is_verified = True
    user.is_active = user.approval_status == "approved"
    db.commit()
    log_action(db, "email_verified", user_id=user.id, institution_id=user.institution_id)
    message = (
        "Email verified. Your lecturer registration is awaiting institutional approval."
        if user.requested_role == "lecturer" and user.approval_status == "pending"
        else "Email verified. You can now log in."
    )
    return {"message": message}


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == str(payload.email).strip().lower()).first()
    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        log_action(db, "login_failed", success=False)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.approval_status == "pending":
        raise HTTPException(status_code=403, detail="Your lecturer registration is awaiting institutional approval.")
    if user.approval_status == "rejected":
        raise HTTPException(status_code=403, detail="Your lecturer registration was not approved. Contact your institution.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account not active.")
    user.last_login_at = datetime.now(timezone.utc); db.commit()
    roles = [r.name for r in user.roles]
    access = create_access_token({"sub": str(user.id), "roles": roles, "institution_id": user.institution_id})
    refresh = create_refresh_token({"sub": str(user.id)})
    log_action(db, "login_success", user_id=user.id, institution_id=user.institution_id)
    return TokenResponse(access_token=access, refresh_token=refresh, user_id=user.id, role=roles[0] if roles else None)
