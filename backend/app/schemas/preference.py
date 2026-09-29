from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel


class PreferenceResponse(BaseModel):
    user_id: str
    profile_version: int
    algorithm_version: str
    computed_at: datetime
    long_term_preferences: Dict[str, float]
    short_term_preferences: Dict[str, float]
    recent_interactions_count: int
    total_interactions_count: int


class ProfileResetResponse(BaseModel):
    message: str
    user_id: str
    profile_version: int
    reset_at: datetime
