from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


lecturer_program_assignments = Table(
    "lecturer_program_assignments",
    Base.metadata,
    Column("lecturer_id", Integer, ForeignKey("lecturers.id", ondelete="CASCADE"), nullable=False),
    Column("program_id", Integer, ForeignKey("academic_programs.id", ondelete="CASCADE"), nullable=False),
    PrimaryKeyConstraint("lecturer_id", "program_id"),
    mysql_engine="InnoDB",
)


class Faculty(Base, TimestampMixin):
    __tablename__ = "faculties"
    __table_args__ = (
        UniqueConstraint("institution_id", "code", name="uq_faculty_institution_code"),
        {"mysql_engine": "InnoDB"},
    )

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    institution = relationship("Institution")
    departments = relationship("Department", back_populates="faculty")
    programs = relationship("AcademicProgram", back_populates="faculty")


class AcademicProgram(Base, TimestampMixin):
    __tablename__ = "academic_programs"
    __table_args__ = (
        UniqueConstraint("institution_id", "code", name="uq_program_institution_code"),
        {"mysql_engine": "InnoDB"},
    )

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    faculty_id = Column(Integer, ForeignKey("faculties.id", ondelete="SET NULL"), nullable=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    award_level = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    institution = relationship("Institution")
    faculty = relationship("Faculty", back_populates="programs")
    department = relationship("Department")
    courses = relationship("Course", back_populates="program")
    lecturers = relationship(
        "Lecturer",
        secondary=lecturer_program_assignments,
        back_populates="programs",
    )
