from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    faculty_id = Column(
        Integer,
        ForeignKey("faculties.id", ondelete="SET NULL", name="fk_departments_faculty_id_faculties"),
        nullable=True,
        index=True,
    )
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    institution = relationship("Institution", back_populates="departments")
    faculty = relationship("Faculty", back_populates="departments")
    courses = relationship("Course", back_populates="department")
    users = relationship("User", back_populates="department")

    __table_args__ = (
        # unique code per institution
        {"mysql_engine": "InnoDB"},
    )
