from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    gender = Column(String(30), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    address = Column(Text, nullable=True)
    biography = Column(Text, nullable=True)
    profile_picture_path = Column(String(500), nullable=True)

    user = relationship("User", back_populates="profile")


class StudentProfile(Base, TimestampMixin):
    __tablename__ = "student_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=True, unique=True, index=True)
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_phone = Column(String(50), nullable=True)
    emergency_contact_relation = Column(String(100), nullable=True)
    admission_date = Column(Date, nullable=True)
    academic_status = Column(String(50), nullable=True)
    academic_progress_summary = Column(Text, nullable=True)
    compliance_status = Column(String(50), nullable=True)

    user = relationship("User", back_populates="student_profile_detail")
    student = relationship("Student")


class LecturerProfile(Base, TimestampMixin):
    __tablename__ = "lecturer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    lecturer_id = Column(Integer, ForeignKey("lecturers.id", ondelete="CASCADE"), nullable=True, unique=True, index=True)
    professional_title = Column(String(100), nullable=True)
    professional_details = Column(Text, nullable=True)
    office_location = Column(String(255), nullable=True)
    office_hours = Column(String(255), nullable=True)

    user = relationship("User", back_populates="lecturer_profile_detail")
    lecturer = relationship("Lecturer")


class StaffProfile(Base, TimestampMixin):
    __tablename__ = "staff_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    staff_role = Column(String(50), nullable=False, index=True)
    staff_number = Column(String(50), nullable=True, index=True)
    job_title = Column(String(255), nullable=True)
    office = Column(String(255), nullable=True)
    responsibilities = Column(Text, nullable=True)

    user = relationship("User", back_populates="staff_profile_detail")
