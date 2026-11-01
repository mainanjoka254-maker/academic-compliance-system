from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional, List, Literal
from datetime import datetime

from app.schemas.common import ORMModel


class InstitutionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: str = Field(min_length=2, max_length=50)
    type: str = Field(default="university", min_length=2, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=50)
    address: Optional[str] = Field(default=None, max_length=2000)
    country: Optional[str] = Field(default=None, max_length=100)

    @field_validator("name", "code", "type")
    @classmethod
    def strip_values(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Value must contain at least two non-whitespace characters")
        return value

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        if len(value) < 2:
            raise ValueError("Institution code must contain at least two characters")
        if not value.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Institution code may contain only letters, numbers, hyphens, and underscores")
        return value.upper()


class InstitutionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    code: Optional[str] = Field(default=None, min_length=2, max_length=50)
    type: Optional[str] = Field(default=None, min_length=2, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=50)
    address: Optional[str] = Field(default=None, max_length=2000)
    country: Optional[str] = Field(default=None, max_length=100)
    is_active: Optional[bool] = None

    @field_validator("name", "type")
    @classmethod
    def strip_optional_values(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Value must contain at least two non-whitespace characters")
        return value

    @field_validator("code")
    @classmethod
    def normalize_optional_code(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Institution code must contain at least two characters")
        if not value.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Institution code may contain only letters, numbers, hyphens, and underscores")
        return value.upper()

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set:
            raise ValueError("At least one institution field must be provided")
        return self


class InstitutionAdministratorCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Full name must contain at least two non-whitespace characters")
        return value


class InstitutionAdministratorStatus(BaseModel):
    is_active: bool


class InstitutionOut(ORMModel):
    id: int
    name: str
    code: str
    type: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    is_active: bool
    subscription_status: str
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    institution_id: Optional[int] = None
    department_id: Optional[int] = None
    role: Literal["super_admin", "university_admin", "registrar", "compliance_officer", "lecturer", "student"] = "student"
    phone: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    phone: Optional[str] = None
    institution_id: Optional[int] = None
    department_id: Optional[int] = None
    is_active: bool
    is_verified: bool
    roles: List[str] = []
    created_at: datetime


class RoleAssign(BaseModel):
    user_id: int
    role_name: Literal["super_admin", "university_admin", "registrar", "compliance_officer", "lecturer", "student"]
    institution_id: Optional[int] = None
