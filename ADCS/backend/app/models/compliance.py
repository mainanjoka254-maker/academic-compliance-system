from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Date, DateTime, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base
from app.models.base import TimestampMixin


class AcademicPolicy(Base, TimestampMixin):
    __tablename__ = "academic_policies"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    version = Column(String(20), default="1.0")
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    effective_date = Column(Date, nullable=True)

    institution = relationship("Institution", back_populates="academic_policies")


class ComplianceRule(Base, TimestampMixin):
    __tablename__ = "compliance_rules"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    rule_type = Column(String(50), nullable=False)
    threshold_value = Column(Float, nullable=True)
    weight = Column(Float, default=1.0)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    severity = Column(String(20), default="moderate")

    institution = relationship("Institution", back_populates="compliance_rules")


class ComplianceIncident(Base, TimestampMixin):
    __tablename__ = "compliance_incidents"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True, index=True)
    reported_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    incident_type = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)
    status = Column(String(50), default="reported", nullable=False, index=True)
    priority = Column(String(20), default="medium", nullable=False)

    student = relationship("Student")
    course = relationship("Course")
    reporter = relationship("User", foreign_keys=[reported_by])
