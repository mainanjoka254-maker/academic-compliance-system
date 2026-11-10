from datetime import datetime, timedelta
import hashlib
from typing import Optional

from sqlalchemy.orm import Session

from app.models.session import UserSession, LoginHistory
from app.models.activity import UserActivityLog


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_user_session(db: Session, user_id: int, token: str, request=None, expires_minutes: int = 60 * 24) -> UserSession:
    ua = request.headers.get("user-agent") if request else None
    ip = request.client.host if request and request.client else None
    sess = UserSession(
        user_id=user_id,
        session_token_hash=hash_session_token(token),
        device_info=(ua or "")[:255] if ua else None,
        ip_address=ip,
        user_agent=(ua or "")[:500] if ua else None,
        last_active_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=expires_minutes),
        is_active=True,
    )
    db.add(sess)
    return sess


def record_login(db: Session, user_id: Optional[int], email: str, institution_id: Optional[int], success: bool, method: str, request=None, failure_reason: Optional[str] = None):
    ua = request.headers.get("user-agent") if request else None
    ip = request.client.host if request and request.client else None
    db.add(LoginHistory(
        user_id=user_id,
        institution_id=institution_id,
        email=(email or "").lower(),
        success=success,
        method=method,
        ip_address=ip,
        user_agent=(ua or "")[:500] if ua else None,
        failure_reason=(failure_reason or "")[:255] if failure_reason else None,
    ))


def log_activity(db: Session, user_id: int, institution_id: Optional[int], activity_type: str, description: str, ip_address: Optional[str] = None, metadata: Optional[str] = None):
    db.add(UserActivityLog(
        user_id=user_id,
        institution_id=institution_id,
        activity_type=activity_type,
        description=description,
        metadata_json=metadata,
        ip_address=ip_address,
    ))
