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
    date_format = Column(String(30), nullable=False, default="YYYY-MM-DD")
    font_size = Column(String(20), nullable=False, default="medium")
    email_notifications = Column(Boolean, nullable=False, default=True)
    in_app_notifications = Column(Boolean, nullable=False, default=True)
    dashboard_preferences = Column(JSON, nullable=True)
    privacy_preferences = Column(JSON, nullable=True)
    extra = Column(JSON, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="settings")


class UserNotificationPreference(Base):
    __tablename__ = "user_notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    academic_announcements = Column(Boolean, nullable=False, default=True)
    course_notifications = Column(Boolean, nullable=False, default=True)
    registration_notifications = Column(Boolean, nullable=False, default=True)
    attendance_alerts = Column(Boolean, nullable=False, default=True)
    compliance_alerts = Column(Boolean, nullable=False, default=True)
    assessment_notifications = Column(Boolean, nullable=False, default=True)
    security_notifications = Column(Boolean, nullable=False, default=True)
    email_enabled = Column(Boolean, nullable=False, default=True)
    in_app_enabled = Column(Boolean, nullable=False, default=True)
    frequency = Column(String(30), nullable=False, default="immediate")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="notification_preferences")


class UserPrivacyPreference(Base):
    __tablename__ = "user_privacy_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    show_profile_picture = Column(Boolean, nullable=False, default=True)
    show_email = Column(Boolean, nullable=False, default=False)
    show_phone = Column(Boolean, nullable=False, default=False)
    allow_contact = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="privacy_preferences")