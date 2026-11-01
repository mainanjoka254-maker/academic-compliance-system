from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2)
    phone: Optional[str] = Field(default=None, max_length=50)
    institution_id: int
    role_requested: Optional[str] = None
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

    @model_validator(mode="after")
    def validate_registration_role(self):
        if self.role_requested == "lecturer" and not self.staff_number:
            raise ValueError("A staff number is required for lecturer registration")
        if self.role_requested == "student" and self.staff_number is not None:
            raise ValueError("Staff number is only valid for lecturer registration")
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
