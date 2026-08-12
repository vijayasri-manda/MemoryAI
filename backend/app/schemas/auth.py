"""
Pydantic schemas for authentication endpoints.
"""

import re
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_serializer, field_validator


class UserRegisterRequest(BaseModel):
    """Registration request body."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter.")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit.")
        return v


class UserLoginRequest(BaseModel):
    """Login request body (supports email or username)."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Successful login response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    """Public user representation."""
    id: UUID | str
    email: str
    username: str
    full_name: Optional[str] = None
    is_active: bool
    is_verified: bool

    @field_serializer("id")
    def serialize_id(self, v: UUID | str) -> str:
        return str(v)

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
