from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from app.core.database import Base
from app.models.base import TimestampMixin


class GoogleOAuthState(Base, TimestampMixin):
    __tablename__ = "google_oauth_states"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(128), nullable=False, unique=True, index=True)
    nonce = Column(String(128), nullable=False)
    code_verifier = Column(String(128), nullable=False)
    action = Column(String(20), nullable=False)
    institution_id = Column(
        Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    exchange_token_hash = Column(String(64), nullable=True, unique=True)
    exchange_expires_at = Column(DateTime, nullable=True)
    used = Column(Boolean, nullable=False, default=False, index=True)
