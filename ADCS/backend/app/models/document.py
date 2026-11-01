from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class AcademicDocument(Base, TimestampMixin):
    __tablename__ = "academic_documents"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=True, index=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    purpose = Column(String(30), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    storage_key = Column(String(80), nullable=False, unique=True)
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_note = Column(Text, nullable=True)

    student = relationship("Student")
    course = relationship("Course")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    review_history = relationship(
        "DocumentReview",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentReview.created_at",
    )


class DocumentReview(Base, TimestampMixin):
    __tablename__ = "document_reviews"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("academic_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    previous_status = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    note = Column(Text, nullable=True)

    document = relationship("AcademicDocument", back_populates="review_history")
    reviewer = relationship("User")
