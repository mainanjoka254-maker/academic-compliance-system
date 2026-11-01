from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base
from app.models.base import TimestampMixin


class ComplianceCase(Base, TimestampMixin):
    __tablename__ = "compliance_cases"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    incident_id = Column(Integer, ForeignKey("compliance_incidents.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_officer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    case_number = Column(String(50), nullable=False, unique=True, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="reported", nullable=False, index=True)
    priority = Column(String(20), default="medium", nullable=False)
    decision = Column(Text, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    escalated_at = Column(DateTime, nullable=True)

    student = relationship("Student", back_populates="compliance_cases")
    incident = relationship("ComplianceIncident")
    assigned_officer = relationship("User", foreign_keys=[assigned_officer_id])
    investigations = relationship("Investigation", back_populates="case", cascade="all, delete-orphan")
    appeals = relationship("Appeal", back_populates="case", cascade="all, delete-orphan")
    audit_trail = relationship("CaseAudit", back_populates="case", cascade="all, delete-orphan")


class Investigation(Base, TimestampMixin):
    __tablename__ = "investigations"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("compliance_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    investigator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    findings = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)
    status = Column(String(50), default="open", nullable=False)
    completed_at = Column(DateTime, nullable=True)

    case = relationship("ComplianceCase", back_populates="investigations")
    investigator = relationship("User")


class Appeal(Base, TimestampMixin):
    __tablename__ = "appeals"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("compliance_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    submitted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text, nullable=False)
    status = Column(String(50), default="submitted", nullable=False, index=True)
    response = Column(Text, nullable=True)
    responded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    responded_at = Column(DateTime, nullable=True)

    case = relationship("ComplianceCase", back_populates="appeals")
    student = relationship("Student", back_populates="appeals")


class CaseAudit(Base, TimestampMixin):
    __tablename__ = "case_audits"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("compliance_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)

    case = relationship("ComplianceCase", back_populates="audit_trail")
