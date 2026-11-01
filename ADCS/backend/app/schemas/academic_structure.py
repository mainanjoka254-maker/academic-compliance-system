from pydantic import BaseModel, Field


class FacultyCreate(BaseModel):
    institution_id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=50)


class DepartmentCreate(BaseModel):
    institution_id: int | None = Field(default=None, gt=0)
    faculty_id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=500)


class DepartmentFacultyUpdate(BaseModel):
    faculty_id: int | None = Field(default=None, gt=0)


class AcademicProgramCreate(BaseModel):
    institution_id: int | None = Field(default=None, gt=0)
    faculty_id: int | None = Field(default=None, gt=0)
    department_id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    award_level: str | None = Field(default=None, max_length=100)


class LecturerProgramAssignmentUpdate(BaseModel):
    program_ids: list[int] = Field(max_length=100)
