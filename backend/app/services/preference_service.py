import math
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.config import settings
from app.models.interaction import UserInteraction
from app.models.movie import Movie
from app.models.preference import UserPreferenceProfile


def map_interaction_to_strength(interaction_type: str, rating: Optional[float] = None) -> float:
    """Maps interaction to a signed preference strength in [-1.0, 1.0]."""
    itype = interaction_type.lower()
    if itype == "rating" and rating is not None:
        # Scale 1..5 stars into -1.0 .. +1.0 (3.0 is neutral 0.0)
        return max(-1.0, min(1.0, (rating - 3.0) / 2.0))
    elif itype == "like":
        return 1.0
    elif itype == "dislike":
        return -1.0
    elif itype == "watched":
        return 0.3
    elif itype == "dismiss":
        return -0.8
    return 0.0


def calculate_genre_preferences(
    interactions: List[Tuple[UserInteraction, Movie]],
    decay_rate: float = 0.0,
    reference_time: Optional[datetime] = None
) -> Dict[str, float]:
    """Calculates weighted genre scores using optional exponential time decay.
    
    Formula: weight = strength * exp(-decay_rate * age_in_days)
    """
    if not interactions:
        return {}

    now = reference_time or datetime.utcnow()
    genre_scores: Dict[str, float] = {}
    genre_weights: Dict[str, float] = {}

    for inter, movie in interactions:
        strength = map_interaction_to_strength(inter.interaction_type, inter.rating)
        
        # Calculate interaction age in days
        age_days = max(0.0, (now - inter.occurred_at).total_seconds() / 86400.0)
        decay = math.exp(-decay_rate * age_days) if decay_rate > 0 else 1.0
        weight = strength * decay

        if not movie or not movie.genres:
            continue

        genres = [g.strip() for g in movie.genres.split("|") if g.strip() and g.strip() != "(no genres listed)"]
        for g in genres:
            genre_scores[g] = genre_scores.get(g, 0.0) + weight
            genre_weights[g] = genre_weights.get(g, 0.0) + abs(decay)

    # Normalize scores
    normalized: Dict[str, float] = {}
    for g, total_score in genre_scores.items():
        w = genre_weights.get(g, 1.0)
        if w > 0:
            # Round to 3 decimal places for reproducibility & inspectability
            normalized[g] = round(total_score / math.sqrt(w), 3)

    return normalized


class PreferenceService:
    @staticmethod
    def get_latest_profile(db: Session, user_id: str) -> Optional[UserPreferenceProfile]:
        return (
            db.query(UserPreferenceProfile)
            .filter(UserPreferenceProfile.user_id == user_id)
            .order_by(UserPreferenceProfile.profile_version.desc())
            .first()
        )

    @staticmethod
    def update_preference_profile(
        db: Session,
        user_id: str,
        decay_rate: Optional[float] = None,
        algorithm_version: Optional[str] = None
    ) -> UserPreferenceProfile:
        rate = decay_rate if decay_rate is not None else settings.DECAY_RATE
        algo_ver = algorithm_version or settings.DYNAMIC_ALGO_VERSION

        # Fetch all user interactions joined with movies, ordered chronologically
        records = (
            db.query(UserInteraction, Movie)
            .join(Movie, UserInteraction.movie_id == Movie.id)
            .filter(UserInteraction.user_id == user_id)
            .order_by(UserInteraction.occurred_at.asc())
            .all()
        )

        now = datetime.utcnow()
        # 1. Long-term preferences (decay_rate = 0.0, stable history)
        long_term = calculate_genre_preferences(records, decay_rate=0.0, reference_time=now)
        
        # 2. Short-term preferences (time-decayed with configured decay rate)
        short_term = calculate_genre_preferences(records, decay_rate=rate, reference_time=now)

        latest = PreferenceService.get_latest_profile(db, user_id)
        next_version = (latest.profile_version + 1) if latest else 1

        new_profile = UserPreferenceProfile(
            id=str(uuid.uuid4()),
            user_id=user_id,
            profile_version=next_version,
            long_term_preferences_json=long_term,
            short_term_preferences_json=short_term,
            computed_at=now,
            algorithm_version=algo_ver
        )
        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)
        return new_profile

    @staticmethod
    def reset_profile(db: Session, user_id: str) -> UserPreferenceProfile:
        latest = PreferenceService.get_latest_profile(db, user_id)
        next_version = (latest.profile_version + 1) if latest else 1

        reset_profile = UserPreferenceProfile(
            id=str(uuid.uuid4()),
            user_id=user_id,
            profile_version=next_version,
            long_term_preferences_json={},
            short_term_preferences_json={},
            computed_at=datetime.utcnow(),
            algorithm_version=settings.DYNAMIC_ALGO_VERSION + "-reset"
        )
        db.add(reset_profile)
        db.commit()
        db.refresh(reset_profile)
        return reset_profile

    @staticmethod
    def get_combined_preference(
        long_term: Dict[str, float],
        short_term: Dict[str, float],
        short_term_weight: Optional[float] = None
    ) -> Dict[str, float]:
        alpha = short_term_weight if short_term_weight is not None else settings.SHORT_TERM_WEIGHT
        all_genres = set(long_term.keys()).union(set(short_term.keys()))
        combined: Dict[str, float] = {}

        for g in all_genres:
            lt = long_term.get(g, 0.0)
            st = short_term.get(g, 0.0)
            combined[g] = round(alpha * st + (1.0 - alpha) * lt, 3)

        return combined
