from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, Float, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Student(Base, TimestampMixin):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)

    student_number = Column(String(50), nullable=False, index=True)
    program = Column(String(255), nullable=True)
    year_of_study = Column(Integer, nullable=True)
    enrollment_date = Column(Date, nullable=True)
    status = Column(String(50), default="active", nullable=False, index=True)  # active/suspended/graduated

    # Aggregated (cached, recomputed by services)
    attendance_percentage = Column(Float, default=0.0)
    gpa = Column(Float, nullable=True)

    user = relationship("User", back_populates="student_profile")
    institution = relationship("Institution", back_populates="students")
    department = relationship("Department")
    enrollments = relationship("CourseEnrollment", back_populates="student", cascade="all, delete-orphan")
    attendance_records = relationship("AttendanceRecord", back_populates="student", cascade="all, delete-orphan")
    assessment_records = relationship("AssessmentRecord", back_populates="student", cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="student", cascade="all, delete-orphan")
    compliance_cases = relationship("ComplianceCase", back_populates="student", cascade="all, delete-orphan")
    appeals = relationship("Appeal", back_populates="student", cascade="all, delete-orphan")

    __table_args__ = ({"mysql_engine": "InnoDB"},)


class Lecturer(Base, TimestampMixin):
    __tablename__ = "lecturers"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)

    staff_number = Column(String(50), nullable=False, index=True)
    title = Column(String(50), nullable=True)
    specialization = Column(String(255), nullable=True)

    user = relationship("User", back_populates="lecturer_profile")
    institution = relationship("Institution", back_populates="lecturers")
    department = relationship("Department")
    courses = relationship("Course", back_populates="lecturer")
    programs = relationship(
        "AcademicProgram",
        secondary="lecturer_program_assignments",
        back_populates="lecturers",
    )
