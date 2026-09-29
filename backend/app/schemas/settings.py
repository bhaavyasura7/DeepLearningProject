from typing import Optional
from pydantic import BaseModel, Field


class UserSettingsUpdate(BaseModel):
    recommendations_enabled: Optional[bool] = None
    notifications_enabled: Optional[bool] = None
    refresh_frequency: Optional[str] = Field(None, pattern="^(event|daily|paused)$")
    notification_cooldown: Optional[int] = Field(None, ge=1, le=1440, description="Cooldown in minutes between 1 and 1440")
