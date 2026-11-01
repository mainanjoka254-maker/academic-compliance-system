from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal, Self
from datetime import date

from app.schemas.common import ORMModel


class DepartmentCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None


class DepartmentOut(ORMModel):
    id: int
    institution_id: int
    name: str
    code: str
    description: Optional[str] = None
    is_active: bool


class StudentCreate(BaseModel):
    user_id: int
    student_number: str
    department_id: Optional[int] = None
    program: Optional[str] = None
    year_of_study: Optional[int] = None


class StudentOut(ORMModel):
    id: int
    institution_id: int
    user_id: int
    student_number: str
    program: Optional[str] = None
    year_of_study: Optional[int] = None
    status: str
    attendance_percentage: float
    gpa: Optional[float] = None
    full_name: Optional[str] = None
    email: Optional[str] = None


class LecturerCreate(BaseModel):
    user_id: int
    staff_number: str
    department_id: Optional[int] = None
    title: Optional[str] = None
    specialization: Optional[str] = None


class LecturerOut(ORMModel):
    id: int
    institution_id: int
    user_id: int
    staff_number: str
    title: Optional[str] = None
    specialization: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None


class CourseCreate(BaseModel):
    institution_id: Optional[int] = None
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    department_id: Optional[int] = None
    term_id: Optional[int] = None
    lecturer_id: Optional[int] = None
    program_id: Optional[int] = None
    credits: int = Field(default=3, ge=1, le=100)
    description: Optional[str] = None


class CourseOut(ORMModel):
    id: int
    institution_id: int
    code: str
    name: str
    credits: int
    department_id: Optional[int] = None
    term_id: Optional[int] = None
    lecturer_id: Optional[int] = None
    program_id: Optional[int] = None
    is_active: bool


class AcademicTermCreate(BaseModel):
    institution_id: Optional[int] = None
    name: str = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date
    is_current: bool = False

    @model_validator(mode="after")
    def validate_date_range(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class AcademicTermOut(ORMModel):
    id: int
    institution_id: int
    name: str
    start_date: date
    end_date: date
    is_current: bool


class EnrollmentCreate(BaseModel):
    student_id: int
    course_id: int


class AttendanceCreate(BaseModel):
    student_id: int
    course_id: int
    date: date
    status: Literal["present", "absent", "late", "excused"] = "present"


class AssessmentCreate(BaseModel):
    student_id: int
    course_id: int
    title: str = Field(min_length=1, max_length=255)
    assessment_type: Literal["assignment", "exam", "quiz", "project"] = "assignment"
    max_score: float = Field(default=100.0, gt=0)
    score: Optional[float] = Field(default=None, ge=0)
    submitted: bool = False
    due_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_score_range(self) -> Self:
        if self.score is not None and self.score > self.max_score:
            raise ValueError("score cannot exceed max_score")
        return self
