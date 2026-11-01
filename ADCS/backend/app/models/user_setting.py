from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class UserSetting(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    theme = Column(String(20), nullable=False, default="system")
    language = Column(String(10), nullable=False, default="en")
    timezone = Column(String(50), nullable=False, default="Africa/Nairobi")
    email_notifications = Column(Boolean, nullable=False, default=True)
    in_app_notifications = Column(Boolean, nullable=False, default=True)
    extra = Column(JSON, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)