from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserSettingsResponse(BaseModel):
    recommendations_enabled: bool
    notifications_enabled: bool
    refresh_frequency: str
    notification_cooldown: int

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: str
    email: str
    status: str
    created_at: datetime
    settings: Optional[UserSettingsResponse] = None

    class Config:
        from_attributes = True
