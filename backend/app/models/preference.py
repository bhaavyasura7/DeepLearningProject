import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class UserPreferenceProfile(Base):
    __tablename__ = "user_preference_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_version = Column(Integer, nullable=False, default=1)
    long_term_preferences_json = Column(JSON, nullable=False, default=dict)
    short_term_preferences_json = Column(JSON, nullable=False, default=dict)
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    algorithm_version = Column(String(100), nullable=False)

    user = relationship("User", back_populates="preference_profiles")

    __table_args__ = (
        Index("idx_user_profile_version", "user_id", "profile_version"),
    )
