from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, Float, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base
from app.models.base import TimestampMixin


class AcademicTerm(Base, TimestampMixin):
    __tablename__ = "academic_terms"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)  # e.g. "2025/2026 Semester 1"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_current = Column(Boolean, default=False, nullable=False, index=True)

    institution = relationship("Institution", back_populates="academic_terms")
    courses = relationship("Course", back_populates="term")


class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    term_id = Column(Integer, ForeignKey("academic_terms.id", ondelete="SET NULL"), nullable=True, index=True)
    lecturer_id = Column(Integer, ForeignKey("lecturers.id", ondelete="SET NULL"), nullable=True, index=True)
    program_id = Column(
        Integer,
        ForeignKey(
            "academic_programs.id",
            ondelete="SET NULL",
            name="fk_courses_program_id_academic_programs",
        ),
        nullable=True,
        index=True,
    )

    code = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    credits = Column(Integer, default=3)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    institution = relationship("Institution", back_populates="courses")
    department = relationship("Department", back_populates="courses")
    term = relationship("AcademicTerm", back_populates="courses")
    lecturer = relationship("Lecturer", back_populates="courses")
    program = relationship("AcademicProgram", back_populates="courses")
    enrollments = relationship("CourseEnrollment", back_populates="course", cascade="all, delete-orphan")
    attendance_records = relationship("AttendanceRecord", back_populates="course", cascade="all, delete-orphan")
    assessment_records = relationship("AssessmentRecord", back_populates="course", cascade="all, delete-orphan")


class CourseEnrollment(Base, TimestampMixin):
    __tablename__ = "course_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default="enrolled", nullable=False)  # enrolled/dropped/completed

    student = relationship("Student", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")

    __table_args__ = ({"mysql_engine": "InnoDB"},)


class AttendanceRecord(Base, TimestampMixin):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="present")  # present/absent/late/excused
    recorded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    student = relationship("Student", back_populates="attendance_records")
    course = relationship("Course", back_populates="attendance_records")


class AssessmentRecord(Base, TimestampMixin):
    __tablename__ = "assessment_records"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    assessment_type = Column(String(50), default="assignment")  # assignment/exam/quiz/project
    max_score = Column(Float, default=100.0)
    score = Column(Float, nullable=True)
    submitted = Column(Boolean, default=False, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    due_date = Column(Date, nullable=True)
    recorded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    student = relationship("Student", back_populates="assessment_records")
    course = relationship("Course", back_populates="assessment_records")
