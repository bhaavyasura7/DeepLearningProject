import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, UniqueConstraint, Index, Text
from sqlalchemy.orm import relationship
from app.database import Base


class RecommendationBatch(Base):
    __tablename__ = "recommendation_batches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_version = Column(Integer, nullable=False)
    algorithm_version = Column(String(100), nullable=False)
    trigger_type = Column(String(50), nullable=False)  # "onboarding", "interaction", "schedule", "manual"
    status = Column(String(50), default="pending", nullable=False)  # "pending", "completed", "failed"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="recommendation_batches")
    items = relationship("RecommendationItem", back_populates="batch", cascade="all, delete-orphan", order_by="RecommendationItem.rank")
    notifications = relationship("Notification", back_populates="batch", cascade="all, delete-orphan")


class RecommendationItem(Base):
    __tablename__ = "recommendation_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id = Column(String(36), ForeignKey("recommendation_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    movie_id = Column(String(36), ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True)
    rank = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    explanation = Column(Text, nullable=False)
    feedback_status = Column(String(50), nullable=True)  # "liked", "disliked", "watched", "dismissed"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    batch = relationship("RecommendationBatch", back_populates="items")
    movie = relationship("Movie", back_populates="recommendation_items")

    __table_args__ = (
        UniqueConstraint("batch_id", "movie_id", name="uq_batch_movie"),
        UniqueConstraint("batch_id", "rank", name="uq_batch_rank"),
    )
