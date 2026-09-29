import math
from collections import defaultdict
from typing import Dict, List, Set, Tuple


class PopularityRecommender:
    """Baseline 1: Recommends globally most popular movies with high ratings."""

    def __init__(self, movies: Dict[int, dict], train_ratings: Dict[int, List[dict]]):
        self.movies = movies
        # Count positive ratings (>= 3.5)
        movie_counts = defaultdict(float)
        for uid, ratings in train_ratings.items():
            for r in ratings:
                if r["rating"] >= 3.5:
                    movie_counts[r["movieId"]] += 1.0

        # Sort candidate movies by frequency
        self.ranked_movie_ids = sorted(
            movie_counts.keys(),
            key=lambda mid: (movie_counts[mid], self.movies.get(mid, {}).get("title", "")),
            reverse=True
        )

    def recommend(self, user_id: int, user_train_ratings: List[dict], top_k: int = 10) -> List[int]:
        watched = {r["movieId"] for r in user_train_ratings}
        candidates = [mid for mid in self.ranked_movie_ids if mid not in watched]
        return candidates[:top_k]


class ContentBasedRecommender:
    """Baseline 2: Content-based filtering using genre profile matching."""

    def __init__(self, movies: Dict[int, dict]):
        self.movies = movies
        # Precompute genre sets
        self.movie_genres = {}
        for mid, mdata in movies.items():
            raw_genres = mdata.get("genres", "")
            self.movie_genres[mid] = set(g.strip() for g in raw_genres.split("|") if g.strip())

    def recommend(self, user_id: int, user_train_ratings: List[dict], top_k: int = 10) -> List[int]:
        watched = {r["movieId"] for r in user_train_ratings}
        # Build user genre vector
        user_genre_scores = defaultdict(float)
        for r in user_train_ratings:
            mid = r["movieId"]
            weight = (r["rating"] - 3.0) / 2.0
            for g in self.movie_genres.get(mid, []):
                user_genre_scores[g] += weight

        scored_candidates = []
        for mid, genres in self.movie_genres.items():
            if mid in watched:
                continue
            score = sum(user_genre_scores.get(g, 0.0) for g in genres)
            scored_candidates.append((mid, score))

        scored_candidates.sort(key=lambda x: (x[1], x[0]), reverse=True)
        return [mid for mid, _ in scored_candidates[:top_k]]


class StaticTPRAAgent:
    """Baseline 3: T-PRA base agent using static historical preference memory."""

    def __init__(self, movies: Dict[int, dict]):
        self.movies = movies
        self.movie_genres = {
            mid: set(g.strip() for g in mdata.get("genres", "").split("|") if g.strip())
            for mid, mdata in movies.items()
        }

    def recommend(self, user_id: int, user_train_ratings: List[dict], top_k: int = 10) -> List[int]:
        watched = {r["movieId"] for r in user_train_ratings}
        genre_scores = defaultdict(float)
        
        # Static prompt context: uniform historical accumulation without recency decay
        for r in user_train_ratings:
            weight = (r["rating"] - 3.0) / 2.0
            for g in self.movie_genres.get(r["movieId"], []):
                genre_scores[g] += weight

        scored = []
        for mid, genres in self.movie_genres.items():
            if mid in watched:
                continue
            s = sum(genre_scores.get(g, 0.0) for g in genres)
            scored.append((mid, s))

        scored.sort(key=lambda x: (x[1], x[0]), reverse=True)
        return [mid for mid, _ in scored[:top_k]]


class DynamicMemoryTPRAAgent:
    """Proposed Extension: T-PRA agent with dynamic two-tier preference memory."""

    def __init__(self, movies: Dict[int, dict], decay_rate: float = 0.05, short_term_weight: float = 0.6):
        self.movies = movies
        self.decay_rate = decay_rate
        self.short_term_weight = short_term_weight
        self.movie_genres = {
            mid: set(g.strip() for g in mdata.get("genres", "").split("|") if g.strip())
            for mid, mdata in movies.items()
        }

    def recommend(self, user_id: int, user_train_ratings: List[dict], top_k: int = 10) -> List[int]:
        if not user_train_ratings:
            return []

        watched = {r["movieId"] for r in user_train_ratings}
        # Reference timestamp is max timestamp in train sequence
        max_ts = max(r["timestamp"] for r in user_train_ratings)

        long_term = defaultdict(float)
        short_term = defaultdict(float)

        for r in user_train_ratings:
            strength = (r["rating"] - 3.0) / 2.0
            age_days = max(0.0, (max_ts - r["timestamp"]) / 86400.0)
            decay = math.exp(-self.decay_rate * age_days)

            for g in self.movie_genres.get(r["movieId"], []):
                long_term[g] += strength
                short_term[g] += strength * decay

        # Combine long-term and short-term
        all_genres = set(long_term.keys()).union(set(short_term.keys()))
        combined = {}
        for g in all_genres:
            combined[g] = (
                self.short_term_weight * short_term.get(g, 0.0)
                + (1.0 - self.short_term_weight) * long_term.get(g, 0.0)
            )

        scored = []
        for mid, genres in self.movie_genres.items():
            if mid in watched:
                continue
            s = sum(combined.get(g, 0.0) for g in genres)
            scored.append((mid, s))

        scored.sort(key=lambda x: (x[1], x[0]), reverse=True)
        return [mid for mid, _ in scored[:top_k]]
