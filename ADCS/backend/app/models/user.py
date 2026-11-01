from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base
from app.models.base import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)

    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=True)
    google_sub = Column(String(255), nullable=True, unique=True, index=True)
    auth_provider = Column(String(30), nullable=False, default="password", server_default="password")
    requested_role = Column(String(30), nullable=True)
    requested_staff_number = Column(String(50), nullable=True)
    approval_status = Column(String(30), nullable=False, default="approved", server_default="approved")
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    is_active = Column(Boolean, default=False, nullable=False, index=True)  # activated after OTP
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)  # platform-level

    last_login_at = Column(DateTime, nullable=True)
    deactivated_at = Column(DateTime, nullable=True)
    deactivation_reason = Column(Text, nullable=True)

    institution = relationship("Institution", back_populates="users")
    department = relationship("Department", back_populates="users")
    roles = relationship("Role", secondary="user_roles", back_populates="users")
    student_profile = relationship("Student", back_populates="user", uselist=False)
    lecturer_profile = relationship("Lecturer", back_populates="user", uselist=False)

    # audit
    audit_logs = relationship("AuditLog", back_populates="user")
