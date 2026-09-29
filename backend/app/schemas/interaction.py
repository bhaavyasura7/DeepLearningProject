from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class InteractionTypeEnum(str, Enum):
    RATING = "rating"
    LIKE = "like"
    DISLIKE = "dislike"
    WATCHED = "watched"
    DISMISS = "dismiss"


class InteractionCreate(BaseModel):
    movie_id: str
    interaction_type: InteractionTypeEnum
    rating: Optional[float] = Field(None, ge=0.5, le=5.0, description="Rating from 0.5 to 5.0")
    occurred_at: Optional[datetime] = None
    idempotency_key: Optional[str] = None
    source: Optional[str] = "web"


class InteractionResponse(BaseModel):
    id: str
    user_id: str
    movie_id: str
    interaction_type: str
    rating: Optional[float] = None
    occurred_at: datetime
    source: str
    idempotency_key: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InteractionListResponse(BaseModel):
    items: List[InteractionResponse]
    total: int
    page: int
    page_size: int
