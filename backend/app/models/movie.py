import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Movie(Base):
    __tablename__ = "movies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    movielens_id = Column(Integer, unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False, index=True)
    release_year = Column(Integer, nullable=True, index=True)
    genres = Column(String(500), nullable=False, default="")  # e.g. "Action|Comedy"
    metadata_json = Column(JSON, nullable=True)  # Additional poster, synopsis, tag info
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    interactions = relationship("UserInteraction", back_populates="movie", cascade="all, delete-orphan")
    recommendation_items = relationship("RecommendationItem", back_populates="movie")
