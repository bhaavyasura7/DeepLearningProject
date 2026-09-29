from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class JobResponse(BaseModel):
    id: str
    job_type: str
    user_id: Optional[str] = None
    idempotency_key: str
    status: str
    attempts: int
    scheduled_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_error: Optional[str] = None

    class Config:
        from_attributes = True
