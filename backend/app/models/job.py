import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Index
from app.database import Base


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_type = Column(String(50), nullable=False, index=True)  # "preference.update", "recommendation.generate", "notification.create"
    user_id = Column(String(36), nullable=True, index=True)
    idempotency_key = Column(String(150), unique=True, index=True, nullable=False)
    status = Column(String(50), default="queued", nullable=False, index=True)  # "queued", "running", "succeeded", "failed", "retry_wait"
    attempts = Column(Integer, default=0, nullable=False)
    scheduled_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_job_status_scheduled", "status", "scheduled_at"),
    )
