"""Request/response models for authentication and account management."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    grade: Optional[str] = Field(default=None, max_length=40)
    board: Optional[str] = Field(default=None, max_length=40)
    preferred_language: str = Field(default="en", max_length=10)
    preferred_level: Literal["beginner", "intermediate", "advanced"] = "beginner"
    # Optional at signup: a mentor (parent/guardian/tutor) notified by email if
    # the learner repeatedly struggles with a concept and the FSM escalates.
    mentor_name: Optional[str] = Field(default=None, max_length=120)
    mentor_email: Optional[EmailStr] = Field(default=None)

    @field_validator("full_name")
    @classmethod
    def _clean_name(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("Full name is required")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=10)


class ResendOTPRequest(BaseModel):
    email: EmailStr
    purpose: Literal["verify_email", "reset_password"] = "verify_email"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=10)
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    initials: str
    role: str
    is_verified: bool
    preferred_language: str
    preferred_level: str
    preferred_style: Optional[str] = None
    default_time_budget_min: int
    grade: Optional[str] = None
    board: Optional[str] = None
    avatar_color: str
    mentor_name: Optional[str] = None
    mentor_email: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class MessageResponse(BaseModel):
    status: str = "ok"
    message: str
    # Populated only when SMTP is unconfigured, so a local demo can still proceed.
    dev_otp: Optional[str] = None


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    grade: Optional[str] = Field(default=None, max_length=40)
    board: Optional[str] = Field(default=None, max_length=40)
    preferred_language: Optional[str] = Field(default=None, max_length=10)
    preferred_level: Optional[Literal["beginner", "intermediate", "advanced"]] = None
    preferred_style: Optional[str] = Field(default=None, max_length=40)
    default_time_budget_min: Optional[int] = Field(default=None, ge=5, le=120)
    avatar_color: Optional[str] = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    mentor_name: Optional[str] = Field(default=None, max_length=120)
    mentor_email: Optional[EmailStr] = Field(default=None)


class SessionOut(BaseModel):
    id: str
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: datetime
    current: bool = False


class DeleteAccountRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)
    confirm: Literal["DELETE"]
