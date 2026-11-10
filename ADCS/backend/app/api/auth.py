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
from app.services.account_service import record_login, create_user_session
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
    requested_role = (payload.role_requested or "student").strip().lower()
    self_register_roles = {"student", "lecturer", "registrar", "compliance_officer", "university_admin"}
    staff_request_roles = {"lecturer", "registrar", "compliance_officer", "university_admin"}
    if requested_role not in self_register_roles:
        raise HTTPException(status_code=403, detail="This role cannot be self-registered")
    if requested_role in staff_request_roles and not payload.staff_number:
        raise HTTPException(status_code=422, detail="A staff/employee number is required for institutional staff registration")
    if requested_role == "student" and payload.staff_number is not None:
        raise HTTPException(status_code=422, detail="Staff number is only valid for staff registration")
    normalized_email = str(payload.email).strip().lower()
    if db.query(User).filter(User.email == normalized_email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    from app.models.institution import Institution
    inst = db.query(Institution).filter(Institution.id == payload.institution_id, Institution.is_active == True).first()
    if not inst:
        raise HTTPException(status_code=400, detail="Invalid or inactive institution")
    staff_request = requested_role in staff_request_roles
    if staff_request:
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
        requested_role=requested_role if staff_request else None,
        requested_staff_number=payload.staff_number if staff_request else None,
        approval_status="pending" if staff_request else "approved",
        is_active=False,
        is_verified=False,
    )
    db.add(user); db.commit(); db.refresh(user)
    if not staff_request:
        role = _get_or_create_role(db, "student")
        user.roles.append(role); db.commit()
        from app.models.student import Student
        sp = Student(user_id=user.id, institution_id=payload.institution_id, student_number=f"STU{user.id:06d}", status="active")
        db.add(sp); db.commit()
    otp = f"{secrets.randbelow(1_000_000):06d}"
    tok = EmailVerificationToken(user_id=user.id, token=otp, expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.EMAIL_OTP_EXPIRE_MINUTES))
    db.add(tok); db.commit()
    if not send_email(normalized_email, "ADCS Email Verification", f"Your verification code is: {otp}"):
        log_action(db, "verification_email_delivery_failed", user_id=user.id, institution_id=payload.institution_id, success=False)
        raise HTTPException(status_code=503, detail="Your account was created, but verification email delivery failed. Configure SMTP and request a new code.")
    create_notification(db, user.id, "Verify your account", "A verification code was sent to your email address.", type_="account_verification", institution_id=payload.institution_id)
    log_action(db, "user_registered", user_id=user.id, institution_id=payload.institution_id)
    message = (
        f"{requested_role.replace('_', ' ').title()} account request submitted. Verify your email; institutional approval is also required before you can sign in."
        if staff_request
        else "Registration successful. Please verify your email with the OTP sent."
    )
    return {"message": message, "user_id": user.id}


@router.get("/account-status")
@limiter.limit(settings.RATE_LIMIT_ACCOUNT_STATUS)
def account_status(email: str, request: Request, db: Session = Depends(get_db)):
    """Public, non-enumerating status check for a registration (no sensitive data leaked)."""
    normalized_email = str(email).strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user:
        return {"found": False, "message": "No account request found for this email address."}
    status_label = "active"
    if not user.is_verified:
        status_label = "email_verification_required"
    elif user.approval_status == "pending":
        status_label = "pending_approval"
    elif user.approval_status == "rejected":
        status_label = "not_approved"
    elif not user.is_active:
        status_label = "inactive"
    role = user.requested_role or ([r.name for r in user.roles][0] if user.roles else None)
    return {
        "found": True,
        "status": status_label,
        "requested_role": role,
        "is_verified": user.is_verified,
        "approval_status": user.approval_status,
    }


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
    normalized_email = str(payload.email).strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        record_login(db, getattr(user, "id", None), normalized_email, getattr(user, "institution_id", None) if user else None, False, "password", request=request, failure_reason="invalid_credentials")
        log_action(db, "login_failed", user_id=getattr(user, "id", None), institution_id=getattr(user, "institution_id", None) if user else None, success=False)
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_verified:
        record_login(db, user.id, normalized_email, user.institution_id, False, "password", request=request, failure_reason="email_not_verified")
        db.commit()
        raise HTTPException(status_code=403, detail="Please verify your email address before signing in.")
    if user.approval_status == "pending":
        role_label = (user.requested_role or "account").replace("_", " ")
        record_login(db, user.id, normalized_email, user.institution_id, False, "password", request=request, failure_reason="pending_approval")
        db.commit()
        raise HTTPException(status_code=403, detail=f"Your {role_label} account request is awaiting institutional approval.")
    if user.approval_status == "rejected":
        record_login(db, user.id, normalized_email, user.institution_id, False, "password", request=request, failure_reason="not_approved")
        db.commit()
        raise HTTPException(status_code=403, detail="Your account request was not approved. Contact your institution.")
    if not user.is_active:
        record_login(db, user.id, normalized_email, user.institution_id, False, "password", request=request, failure_reason="inactive")
        db.commit()
        raise HTTPException(status_code=403, detail="Account not active.")
    user.last_login_at = datetime.now(timezone.utc)
    roles = [r.name for r in user.roles]
    access = create_access_token({"sub": str(user.id), "roles": roles, "institution_id": user.institution_id})
    refresh = create_refresh_token({"sub": str(user.id)})
    create_user_session(db, user.id, access, request=request, expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    record_login(db, user.id, normalized_email, user.institution_id, True, "password", request=request)
    log_action(db, "login_success", user_id=user.id, institution_id=user.institution_id)
    db.commit()
    return TokenResponse(access_token=access, refresh_token=refresh, user_id=user.id, role=roles[0] if roles else None)
