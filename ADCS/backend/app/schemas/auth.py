from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional


# Roles that may be requested via public registration (all require institutional approval except student).
SELF_REGISTER_ROLES = {"student", "lecturer", "registrar", "compliance_officer", "university_admin"}
STAFF_REQUEST_ROLES = {"lecturer", "registrar", "compliance_officer", "university_admin"}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2)
    phone: Optional[str] = Field(default=None, max_length=50)
    institution_id: int
    role_requested: Optional[str] = Field(default="student")
    staff_number: Optional[str] = Field(default=None, min_length=1, max_length=50)

    @field_validator("staff_number")
    @classmethod
    def normalize_staff_number(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Staff number cannot be blank")
        return value

    @field_validator("role_requested")
    @classmethod
    def validate_role_requested(cls, value: Optional[str]) -> str:
        role = (value or "student").strip().lower()
        if role not in SELF_REGISTER_ROLES:
            raise ValueError("This role cannot be self-registered; contact an administrator")
        return role

    @model_validator(mode="after")
    def validate_registration_role(self):
        if self.role_requested in STAFF_REQUEST_ROLES and not self.staff_number:
            raise ValueError("A staff/employee number is required for institutional staff registration")
        if self.role_requested == "student" and self.staff_number is not None:
            raise ValueError("Staff number is only valid for staff registration")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    role: Optional[str] = None


class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str = Field(pattern=r"^\d{6}$")


class ResendOTPRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class RefreshTokenRequest(BaseModel):
    refresh_token: str
