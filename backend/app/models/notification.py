import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recommendation_batch_id = Column(String(36), ForeignKey("recommendation_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    notification_type = Column(String(50), default="recommendation_batch", nullable=False)
    status = Column(String(50), default="unread", nullable=False)  # "unread", "read"
    deduplication_key = Column(String(150), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    delivered_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="notifications")
    batch = relationship("RecommendationBatch", back_populates="notifications")
