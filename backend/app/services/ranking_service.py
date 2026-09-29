import math
from typing import Dict, List, Set, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.models.interaction import UserInteraction
from app.models.movie import Movie
from app.models.preference import UserPreferenceProfile
from app.services.preference_service import PreferenceService


class RankingService:
    @staticmethod
    def get_excluded_movie_ids(db: Session, user_id: str) -> Set[str]:
        """Returns set of movie IDs the user has already rated, liked, disliked, watched, or dismissed."""
        records = (
            db.query(UserInteraction.movie_id)
            .filter(UserInteraction.user_id == user_id)
            .distinct()
            .all()
        )
        return {r[0] for r in records}

    @staticmethod
    def retrieve_candidates(
        db: Session,
        user_id: str,
        limit: int = 100
    ) -> List[Movie]:
        excluded_ids = RankingService.get_excluded_movie_ids(db, user_id)
        query = db.query(Movie)
        if excluded_ids:
            query = query.filter(~Movie.id.in_(excluded_ids))
        
        # Get candidate pool ordered by release year or id
        return query.limit(limit).all()

    @staticmethod
    def score_and_rank_candidates(
        candidates: List[Movie],
        preference_scores: Dict[str, float],
        top_k: int = 10,
        apply_diversity: bool = True
    ) -> List[Tuple[Movie, float, str]]:
        """Scores candidate movies using preference profile and returns (Movie, score, explanation).
        
        Ranking is completely deterministic given fixed inputs.
        """
        if not candidates:
            return []

        scored_candidates = []
        for movie in candidates:
            genres = [g.strip() for g in (movie.genres or "").split("|") if g.strip()]
            matched_genres = []
            score = 0.0

            for g in genres:
                pref = preference_scores.get(g, 0.0)
                if pref > 0:
                    matched_genres.append((g, pref))
                    score += pref
                elif pref < 0:
                    score += pref * 0.8  # Penalty for disliked genres

            # Minor prior boost for modern/classic films with years
            year_boost = 0.0
            if movie.release_year:
                year_boost = min(0.1, max(0.0, (movie.release_year - 1970) * 0.001))
            total_score = round(score + year_boost, 4)

            # Generate grounded explanation
            matched_genres.sort(key=lambda x: x[1], reverse=True)
            if matched_genres:
                top_matches = ", ".join([f"{g} (+{w:.2f})" for g, w in matched_genres[:2]])
                explanation = f"Recommended based on your strong interest in {top_matches}."
            elif genres:
                explanation = f"Recommended discovery title in {genres[0]}."
            else:
                explanation = "Popular title selected for your profile."

            scored_candidates.append((movie, total_score, explanation))

        # Deterministic sorting: score desc, release_year desc, title asc, id asc
        scored_candidates.sort(
            key=lambda x: (
                x[1],
                x[0].release_year or 0,
                x[0].title,
                x[0].id
            ),
            reverse=True
        )

        if not apply_diversity or len(scored_candidates) <= top_k:
            return scored_candidates[:top_k]

        # Apply genre diversity constraint: limit any single primary genre to at most 40% of top_k
        max_per_genre = max(2, int(top_k * 0.4))
        genre_counts: Dict[str, int] = {}
        diverse_selection: List[Tuple[Movie, float, str]] = []
        deferred: List[Tuple[Movie, float, str]] = []

        for item in scored_candidates:
            movie = item[0]
            primary_genre = movie.genres.split("|")[0].strip() if movie.genres else "General"
            count = genre_counts.get(primary_genre, 0)
            if count < max_per_genre:
                diverse_selection.append(item)
                genre_counts[primary_genre] = count + 1
            else:
                deferred.append(item)

            if len(diverse_selection) >= top_k:
                break

        # Fill up if diverse selection has remaining slots
        while len(diverse_selection) < top_k and deferred:
            diverse_selection.append(deferred.pop(0))

        return diverse_selection
