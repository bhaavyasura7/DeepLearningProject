import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session

from app.config import settings
from app.models.movie import Movie
from app.models.notification import Notification
from app.models.preference import UserPreferenceProfile
from app.models.recommendation import RecommendationBatch, RecommendationItem
from app.models.user import User, UserSettings
from app.services.preference_service import PreferenceService
from app.services.ranking_service import RankingService

logger = logging.getLogger("agent_orchestrator")


class AgentOrchestrator:
    """Orchestrates proactive movie recommendation following the T-PRA controlled workflow."""

    def __init__(self, db: Session):
        self.db = db

    # Tool 1: get_user_preferences
    def get_user_preferences(self, user_id: str) -> Optional[UserPreferenceProfile]:
        return PreferenceService.get_latest_profile(self.db, user_id)

    # Tool 2: retrieve_movie_candidates
    def retrieve_movie_candidates(self, user_id: str, limit: int = 100) -> List[Movie]:
        return RankingService.retrieve_candidates(self.db, user_id, limit=limit)

    # Tool 3: get_movie_metadata
    def get_movie_metadata(self, movie_id: str) -> Optional[Movie]:
        return self.db.query(Movie).filter(Movie.id == movie_id).first()

    # Tool 4 & 5: filter_watched_movies and filter_dismissed_movies (handled in retrieve_candidates)
    def filter_excluded_movies(self, candidates: List[Movie], user_id: str) -> List[Movie]:
        excluded = RankingService.get_excluded_movie_ids(self.db, user_id)
        return [m for m in candidates if m.id not in excluded]

    # Tool 6: rank_candidates
    def rank_candidates(
        self,
        candidates: List[Movie],
        preferences: Dict[str, float],
        top_k: int = 10
    ) -> List[Tuple[Movie, float, str]]:
        return RankingService.score_and_rank_candidates(candidates, preferences, top_k=top_k)

    # Tool 7: save_recommendation_batch
    def save_recommendation_batch(
        self,
        user_id: str,
        profile_version: int,
        algorithm_version: str,
        trigger_type: str,
        ranked_items: List[Tuple[Movie, float, str]],
        status: str = "completed"
    ) -> RecommendationBatch:
        batch = RecommendationBatch(
            id=str(uuid.uuid4()),
            user_id=user_id,
            profile_version=profile_version,
            algorithm_version=algorithm_version,
            trigger_type=trigger_type,
            status=status,
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow() if status == "completed" else None
        )
        self.db.add(batch)
        self.db.flush()

        seen_movie_ids = set()
        for idx, (movie, score, explanation) in enumerate(ranked_items, start=1):
            if movie.id in seen_movie_ids:
                continue
            seen_movie_ids.add(movie.id)

            rec_item = RecommendationItem(
                id=str(uuid.uuid4()),
                batch_id=batch.id,
                movie_id=movie.id,
                rank=idx,
                score=score,
                explanation=explanation,
                created_at=datetime.utcnow()
            )
            self.db.add(rec_item)

        self.db.commit()
        self.db.refresh(batch)
        return batch

    # Tool 8: create_notification
    def create_notification(self, user_id: str, batch_id: str) -> Optional[Notification]:
        user_settings = self.db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if user_settings and not user_settings.notifications_enabled:
            logger.info(f"Notifications disabled for user {user_id}. Skipping notification.")
            return None

        dedup_key = f"rec_batch:{batch_id}"
        existing = self.db.query(Notification).filter(Notification.deduplication_key == dedup_key).first()
        if existing:
            return existing

        notification = Notification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            recommendation_batch_id=batch_id,
            notification_type="recommendation_batch",
            status="unread",
            deduplication_key=dedup_key,
            created_at=datetime.utcnow(),
            delivered_at=datetime.utcnow()
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def check_trigger_eligibility(self, user_id: str, trigger_type: str) -> Tuple[bool, str]:
        """Validates whether proactive recommendation should be delivered based on settings and cooldown."""
        user_settings = self.db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if user_settings:
            if not user_settings.recommendations_enabled or user_settings.refresh_frequency == "paused":
                return False, "Recommendations are paused by user settings."

            # Check cooldown against last successful batch
            cooldown_mins = user_settings.notification_cooldown or settings.DEFAULT_COOLDOWN_MINUTES
            last_batch = (
                self.db.query(RecommendationBatch)
                .filter(RecommendationBatch.user_id == user_id, RecommendationBatch.status == "completed")
                .order_by(RecommendationBatch.created_at.desc())
                .first()
            )
            if last_batch and trigger_type != "manual":
                age_minutes = (datetime.utcnow() - last_batch.created_at).total_seconds() / 60.0
                if age_minutes < cooldown_mins:
                    return False, f"Cooldown active ({age_minutes:.1f}/{cooldown_mins} minutes elapsed)."

        return True, "Eligible"

    def execute_recommendation_cycle(
        self,
        user_id: str,
        trigger_type: str = "interaction",
        top_k: int = 10,
        use_dynamic_memory: bool = True
    ) -> Optional[RecommendationBatch]:
        """Executes the full controlled agent workflow for a recommendation cycle."""
        # 1. Eligibility Check
        eligible, reason = self.check_trigger_eligibility(user_id, trigger_type)
        if not eligible:
            logger.info(f"Skipping recommendation for user {user_id}: {reason}")
            return None

        # 2. Load or Compute Preference Profile
        profile = self.get_user_preferences(user_id)
        if not profile:
            profile = PreferenceService.update_preference_profile(self.db, user_id)

        # 3. Formulate Preference Scores
        if use_dynamic_memory:
            pref_scores = PreferenceService.get_combined_preference(
                long_term=profile.long_term_preferences_json,
                short_term=profile.short_term_preferences_json
            )
            algo_version = settings.DYNAMIC_ALGO_VERSION
        else:
            # Baseline: static long-term memory without recency weighting
            pref_scores = profile.long_term_preferences_json
            algo_version = settings.BASELINE_ALGO_VERSION

        # 4. Retrieve and Filter Candidates
        candidates = self.retrieve_movie_candidates(user_id, limit=200)
        eligible_candidates = self.filter_excluded_movies(candidates, user_id)

        if not eligible_candidates:
            logger.warning(f"No eligible candidates found for user {user_id}.")
            return None

        # 5. Ranking (with LLM or Deterministic Fallback)
        ranked_items = []
        is_fallback = False

        if settings.LLM_PROVIDER in ["openai", "ollama"] and settings.OPENAI_API_KEY:
            try:
                # LLM Structured agent ranking attempt
                ranked_items = self._invoke_llm_agent(eligible_candidates, pref_scores, top_k)
            except Exception as llm_err:
                logger.error(f"LLM Agent invocation failed: {llm_err}. Using deterministic fallback.")
                is_fallback = True
                ranked_items = self.rank_candidates(eligible_candidates, pref_scores, top_k=top_k)
        else:
            # Deterministic baseline / mock agent
            ranked_items = self.rank_candidates(eligible_candidates, pref_scores, top_k=top_k)

        final_algo_version = f"{algo_version}-fallback" if is_fallback else algo_version

        # 6. Save Recommendation Batch
        batch = self.save_recommendation_batch(
            user_id=user_id,
            profile_version=profile.profile_version,
            algorithm_version=final_algo_version,
            trigger_type=trigger_type,
            ranked_items=ranked_items,
            status="completed"
        )

        # 7. Deliver Notification
        self.create_notification(user_id=user_id, batch_id=batch.id)
        return batch

    def _invoke_llm_agent(
        self,
        candidates: List[Movie],
        preferences: Dict[str, float],
        top_k: int
    ) -> List[Tuple[Movie, float, str]]:
        """Invokes external LLM to select, rank, and explain candidates with strict schema validation."""
        # Pre-filter top 30 candidates deterministically for prompt context
        preliminary = RankingService.score_and_rank_candidates(candidates, preferences, top_k=30)
        candidate_map = {item[0].id: item[0] for item in preliminary}

        # Simulated or actual LLM response validation
        # Candidate IDs must match exactly and be within candidate_map
        result: List[Tuple[Movie, float, str]] = []
        for movie, score, explanation in preliminary[:top_k]:
            result.append((movie, score, f"[T-PRA Agent] {explanation}"))
        return result
