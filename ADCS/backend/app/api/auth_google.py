import hashlib
import base64
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.id_token import verify_oauth2_token
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, get_current_user
from app.models.institution import Institution
from app.models.oauth import GoogleOAuthState
from app.models.role import Role
from app.models.student import Student
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.services.audit_service import log_action

router = APIRouter(prefix="/auth/google", tags=["Google Authentication"])
_GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
_OAUTH_STATE_COOKIE = "adcs_google_state"
_OAUTH_EXCHANGE_COOKIE = "adcs_google_exchange"


def _google_is_configured() -> bool:
    return bool(
        settings.GOOGLE_CLIENT_ID
        and settings.GOOGLE_CLIENT_SECRET
        and settings.GOOGLE_REDIRECT_URI
    )


def _secure_cookie() -> bool:
    return settings.APP_ENV.lower() not in {"development", "test"}


def _callback_redirect(**params: str) -> RedirectResponse:
    query = urlencode(params)
    target = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/auth/callback"
    return RedirectResponse(f"{target}?{query}" if query else target, status_code=302)


def _start_flow(
    db: Session,
    action: str,
    institution_id: int | None = None,
    user_id: int | None = None,
) -> RedirectResponse:
    if not _google_is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Sign-In is not configured",
        )

    now = datetime.now(timezone.utc)
    db.query(GoogleOAuthState).filter(
        GoogleOAuthState.expires_at < now - timedelta(days=1)
    ).delete(synchronize_session=False)
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    db.add(
        GoogleOAuthState(
            state=state,
            nonce=nonce,
            code_verifier=code_verifier,
            action=action,
            institution_id=institution_id,
            user_id=user_id,
            expires_at=now + timedelta(minutes=10),
        )
    )
    db.commit()

    query = urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
    )
    response = RedirectResponse(
        f"{_GOOGLE_AUTHORIZATION_ENDPOINT}?{query}",
        status_code=302,
    )
    response.set_cookie(
        _OAUTH_STATE_COOKIE,
        state,
        max_age=600,
        httponly=True,
        secure=_secure_cookie(),
        samesite="lax",
        path="/api/v1/auth/google",
    )
    return response


def _exchange_google_code(code: str, code_verifier: str) -> str:
    try:
        response = httpx.post(
            _GOOGLE_TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            },
            timeout=10,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        import logging
        logging.getLogger(__name__).exception("Google token exchange failed: %s", exc)
        if hasattr(exc, "response") and exc.response is not None:
            logging.getLogger(__name__).error("Google token response: %s", exc.response.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google authorization could not be completed",
        ) from exc
    try:
        token_response = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google returned an invalid token response",
        ) from exc
    id_token = token_response.get("id_token")
    if not isinstance(id_token, str) or not id_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google did not return a valid identity token",
        )
    return id_token


def _verify_google_id_token(id_token: str, expected_nonce: str) -> dict:
    try:
        claims = verify_oauth2_token(
            id_token,
            GoogleRequest(),
            audience=settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=60,
        )
    except (GoogleAuthError, ValueError) as exc:
        import logging
        logging.getLogger(__name__).exception("Google ID token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google identity verification failed",
        ) from exc
    if claims.get("nonce") != expected_nonce:
        import logging
        logging.getLogger(__name__).warning("Google nonce mismatch; expected=%s got=%s", expected_nonce, claims.get("nonce"))
    if claims.get("email_verified") is not True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A verified Google email address is required",
        )
    if not isinstance(claims.get("sub"), str) or not isinstance(claims.get("email"), str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google identity is missing required claims",
        )
    return claims


def _is_expired(value: datetime) -> bool:
    return value.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc)


def _issue_login(db: Session, user: User) -> TokenResponse:
    if not user.is_active or not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive or requires email verification",
        )
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    roles = [role.name for role in user.roles]
    return TokenResponse(
        access_token=create_access_token(
            {
                "sub": str(user.id),
                "roles": roles,
                "institution_id": user.institution_id,
            }
        ),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
        user_id=user.id,
        role=roles[0] if roles else None,
    )


def _record_login_grant(db: Session, oauth_state: GoogleOAuthState, user: User) -> str:
    exchange_token = secrets.token_urlsafe(32)
    oauth_state.user_id = user.id
    oauth_state.exchange_token_hash = hashlib.sha256(
        exchange_token.encode("utf-8")
    ).hexdigest()
    oauth_state.exchange_expires_at = datetime.now(timezone.utc) + timedelta(seconds=60)
    oauth_state.used = True
    db.commit()
    return exchange_token


@router.get("")
def google_login(
    institution_id: int | None = None,
    db: Session = Depends(get_db),
):
    return _start_flow(db, "login", institution_id=institution_id)


@router.get("/status")
def google_status():
    return {"enabled": _google_is_configured()}


@router.get("/link")
def google_link(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_verified:
        raise HTTPException(status_code=403, detail="Verify your ADCS account before linking Google")
    return _start_flow(db, "link", user_id=current_user.id)


@router.get("/callback")
def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    if not state:
        response = _callback_redirect(error="oauth_state_invalid")
        response.delete_cookie(_OAUTH_STATE_COOKIE, path="/api/v1/auth/google")
        return response
        response = _callback_redirect(error="oauth_state_invalid")
        response.delete_cookie(_OAUTH_STATE_COOKIE, path="/api/v1/auth/google")
        return response

    oauth_state = db.query(GoogleOAuthState).filter(
        GoogleOAuthState.state == state,
        GoogleOAuthState.used.is_(False),
    ).first()
    if not oauth_state or _is_expired(oauth_state.expires_at):
        response = _callback_redirect(error="oauth_state_expired")
        response.delete_cookie(_OAUTH_STATE_COOKIE, path="/api/v1/auth/google")
        return response
    if error or not code:
        oauth_state.used = True
        db.commit()
        response = _callback_redirect(error="google_authorization_failed")
        response.delete_cookie(_OAUTH_STATE_COOKIE, path="/api/v1/auth/google")
        return response

    try:
        id_token = _exchange_google_code(code, oauth_state.code_verifier)
        claims = _verify_google_id_token(id_token, oauth_state.nonce)
    except HTTPException:
        oauth_state.used = True
        db.commit()
        response = _callback_redirect(error="google_identity_verification_failed")
        response.delete_cookie(_OAUTH_STATE_COOKIE, path="/api/v1/auth/google")
        return response
    google_sub = claims["sub"]
    email = claims["email"].strip().lower()

    if oauth_state.action == "link":
        user = db.query(User).filter(User.id == oauth_state.user_id).first()
        if not user or not user.is_active or not user.is_verified:
            response = _callback_redirect(error="account_not_linkable")
        elif user.email.lower() != email:
            response = _callback_redirect(error="google_email_mismatch")
        else:
            linked_user = db.query(User).filter(User.google_sub == google_sub).first()
            if linked_user and linked_user.id != user.id:
                response = _callback_redirect(error="google_account_already_linked")
            elif user.google_sub and user.google_sub != google_sub:
                response = _callback_redirect(error="different_google_account_linked")
            else:
                user.google_sub = google_sub
                user.auth_provider = "password+google" if user.hashed_password else "google"
                oauth_state.used = True
                db.commit()
                response = _callback_redirect(linked="1")
        if not oauth_state.used:
            oauth_state.used = True
            db.commit()
        response.delete_cookie(_OAUTH_STATE_COOKIE, path="/api/v1/auth/google")
        return response

    user = db.query(User).filter(User.google_sub == google_sub).first()
    if user is None:
        user = db.query(User).filter(User.email == email).first()
        if user:
            if not user.is_active or not user.is_verified:
                response = _callback_redirect(error="account_verification_required")
                oauth_state.used = True
                db.commit()
                response.delete_cookie(_OAUTH_STATE_COOKIE, path="/api/v1/auth/google")
                return response
            if user.google_sub and user.google_sub != google_sub:
                response = _callback_redirect(error="different_google_account_linked")
                oauth_state.used = True
                db.commit()
                response.delete_cookie(_OAUTH_STATE_COOKIE, path="/api/v1/auth/google")
                return response
            user.google_sub = google_sub
            user.auth_provider = "password+google" if user.hashed_password else "google"
            db.commit()
        else:
            institution = db.query(Institution).filter(
                Institution.id == oauth_state.institution_id,
                Institution.is_active.is_(True),
            ).first()
            if not institution:
                response = _callback_redirect(error="institution_selection_required")
                oauth_state.used = True
                db.commit()
                response.delete_cookie(_OAUTH_STATE_COOKIE, path="/api/v1/auth/google")
                return response
            role = db.query(Role).filter(Role.name == "student").first()
            if role is None:
                role = Role(name="student", description="Student", is_system=True)
                db.add(role)
                db.flush()
            user = User(
                email=email,
                hashed_password=None,
                google_sub=google_sub,
                auth_provider="google",
                full_name=claims.get("name") or email,
                avatar_url=claims.get("picture"),
                institution_id=institution.id,
                is_active=True,
                is_verified=True,
            )
            user.roles.append(role)
            db.add(user)
            try:
                db.flush()
                db.add(
                    Student(
                        user_id=user.id,
                        institution_id=institution.id,
                        student_number=f"STU{user.id:06d}",
                        status="active",
                    )
                )
                db.flush()
                db.commit()
            except IntegrityError:
                db.rollback()
                response = _callback_redirect(error="account_already_exists")
                response.delete_cookie(_OAUTH_STATE_COOKIE, path="/api/v1/auth/google")
                return response

    exchange_token = _record_login_grant(db, oauth_state, user)
    log_action(
        db,
        "google_login_success",
        user_id=user.id,
        institution_id=user.institution_id,
    )
    response = _callback_redirect()
    response.set_cookie(
        _OAUTH_EXCHANGE_COOKIE,
        exchange_token,
        max_age=60,
        httponly=True,
        secure=_secure_cookie(),
        samesite="lax",
        path="/api/v1/auth/google/session",
    )
    response.delete_cookie(_OAUTH_STATE_COOKIE, path="/api/v1/auth/google")
    return response


@router.post("/session", response_model=TokenResponse)
def exchange_google_session(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    expected_origin = settings.FRONTEND_BASE_URL.rstrip("/")
    if request.headers.get("origin") != expected_origin:
        raise HTTPException(status_code=403, detail="Invalid session exchange origin")
    raw_token = request.cookies.get(_OAUTH_EXCHANGE_COOKIE)
    if not raw_token:
        raise HTTPException(status_code=401, detail="No Google login session is available")
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    oauth_state = db.query(GoogleOAuthState).filter(
        GoogleOAuthState.exchange_token_hash == token_hash,
        GoogleOAuthState.used.is_(True),
    ).first()
    if (
        not oauth_state
        or not oauth_state.exchange_expires_at
        or _is_expired(oauth_state.exchange_expires_at)
    ):
        raise HTTPException(status_code=401, detail="Google login session is invalid or expired")
    user = db.query(User).filter(User.id == oauth_state.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Google login session is invalid or expired")
    oauth_state.exchange_token_hash = None
    oauth_state.exchange_expires_at = None
    db.commit()
    response.delete_cookie(
        _OAUTH_EXCHANGE_COOKIE,
        path="/api/v1/auth/google/session",
        httponly=True,
        secure=_secure_cookie(),
        samesite="lax",
    )
    return _issue_login(db, user)
