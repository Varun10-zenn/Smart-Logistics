"""Auth schemas."""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(...)
    password: str = Field(..., min_length=1)


class SignupRequest(BaseModel):
    email: EmailStr = Field(...)
    password: str = Field(..., min_length=4)
    full_name: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    username: Optional[str] = None
    email: EmailStr = Field(...)
    password: str = Field(..., min_length=4)

