from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    recommendation_batch_id: str
    notification_type: str
    status: str
    deduplication_key: str
    created_at: datetime
    delivered_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    unread_count: int
