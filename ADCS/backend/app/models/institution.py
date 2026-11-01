from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base
from app.models.base import TimestampMixin


class Institution(Base, TimestampMixin):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    type = Column(String(50), nullable=False, default="university")  # university / college
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    country = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    subscription_status = Column(String(50), default="active")
    subscription_expires_at = Column(DateTime, nullable=True)

    # Relationships
    departments = relationship("Department", back_populates="institution", cascade="all, delete-orphan")
    users = relationship("User", back_populates="institution")
    students = relationship("Student", back_populates="institution")
    lecturers = relationship("Lecturer", back_populates="institution")
    courses = relationship("Course", back_populates="institution")
    academic_terms = relationship("AcademicTerm", back_populates="institution")
    academic_policies = relationship("AcademicPolicy", back_populates="institution")
    compliance_rules = relationship("ComplianceRule", back_populates="institution")
