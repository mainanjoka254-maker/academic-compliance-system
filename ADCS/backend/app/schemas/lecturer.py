from pydantic import BaseModel, EmailStr, Field


class LecturerCreate(BaseModel):
    institution_id: int | None = Field(default=None, gt=0)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    staff_number: str = Field(min_length=1, max_length=50)
    department_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, max_length=50)
    specialization: str | None = Field(default=None, max_length=255)


class LecturerUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    department_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, max_length=50)
    specialization: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class TeachingAssignmentUpdate(BaseModel):
    course_ids: list[int] = Field(max_length=100)


class ProgramAssignmentUpdate(BaseModel):
    program_ids: list[int] = Field(max_length=100)
