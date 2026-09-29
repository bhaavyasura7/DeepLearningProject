from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel
from app.schemas.movie import MovieResponse


class RecommendationFeedbackEnum(str, Enum):
    LIKED = "liked"
    DISLIKED = "disliked"
    WATCHED = "watched"
    DISMISSED = "dismissed"


class RecommendationFeedbackRequest(BaseModel):
    feedback: RecommendationFeedbackEnum


class RecommendationItemResponse(BaseModel):
    id: str
    movie_id: str
    rank: int
    score: float
    explanation: str
    feedback_status: Optional[str] = None
    created_at: datetime
    movie: Optional[MovieResponse] = None

    class Config:
        from_attributes = True


class RecommendationBatchResponse(BaseModel):
    id: str
    user_id: str
    profile_version: int
    algorithm_version: str
    trigger_type: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    items: List[RecommendationItemResponse] = []

    class Config:
        from_attributes = True


class RecommendationRefreshRequest(BaseModel):
    reason: Optional[str] = "manual_refresh"
