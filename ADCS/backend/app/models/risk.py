from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base
from app.models.base import TimestampMixin


class RiskAssessment(Base, TimestampMixin):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    assessed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False, index=True)
    factors = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    attendance_rate = Column(Float, nullable=True)
    missed_assessments = Column(Integer, default=0)
    threshold_snapshot = Column(JSON, nullable=True)
    reviewed = Column(Boolean, default=False, nullable=False)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)

    student = relationship("Student", back_populates="risk_assessments")


class RiskAlert(Base, TimestampMixin):
    __tablename__ = "risk_alerts"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_assessment_id = Column(Integer, ForeignKey("risk_assessments.id", ondelete="SET NULL"), nullable=True)
    level = Column(String(20), nullable=False, index=True)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    read_at = Column(DateTime, nullable=True)

    student = relationship("Student")
