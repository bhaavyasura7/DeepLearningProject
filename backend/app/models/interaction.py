import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class UserInteraction(Base):
    __tablename__ = "user_interactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    movie_id = Column(String(36), ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True)
    interaction_type = Column(String(50), nullable=False)  # "rating", "like", "dislike", "watched", "dismiss"
    rating = Column(Float, nullable=True)  # E.g. 0.5 to 5.0
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    source = Column(String(50), default="web", nullable=False)
    idempotency_key = Column(String(100), nullable=True, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="interactions")
    movie = relationship("Movie", back_populates="interactions")

    __table_args__ = (
        Index("idx_user_interaction_time", "user_id", "occurred_at"),
    )
