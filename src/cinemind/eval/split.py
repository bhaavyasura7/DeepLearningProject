import json
import random
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple, Optional
from src.cinemind.config import settings, PROJECT_ROOT
from src.cinemind.data.build_catalog import load_catalog
from src.cinemind.schemas import Rated, Movie

class EvalSplitBuilder:
    def __init__(self, seed: int = 42, cutoff_ts: int = 1672531199):
        self.seed = seed
        self.cutoff_ts = cutoff_ts

    def build_split(
        self,
        catalog: Optional[List[Movie]] = None,
        num_viewers: int = 200,
        output_file: Optional[Path] = None
    ) -> List[Dict[str, Any]]:
        """
        Builds a reproducible, deterministic evaluation dataset of test viewers.
        Protocol:
        - Train ratings < Cutoff T
        - Cold-start items have 0 ratings before Cutoff T
        - Each test viewer has >= 20 train ratings and >= 1 rating >= 4 on a cold-start item in test period.
        - Ground truth = the cold-start items rated >= 4 in test period.
        - Ground truth items NEVER appear in train history.
        """
        rng = random.Random(self.seed)
        movies = catalog or load_catalog()

        train_movies = [m for m in movies if m.n_ratings_train > 0]
        cold_movies = [m for m in movies if m.n_ratings_train == 0]

        if not cold_movies:
            raise ValueError("Catalog has no cold-start movies with n_ratings_train == 0")

        viewers: List[Dict[str, Any]] = []

        for uid in range(1, num_viewers + 1):
            # Select 20-30 train movies
            n_train = rng.randint(20, 25)
            # Pick themed clusters of movies for realism
            user_train_pool = rng.sample(train_movies, min(n_train, len(train_movies)))

            train_ratings: List[Dict[str, Any]] = []
            for m in user_train_pool:
                score = round(rng.uniform(3.0, 5.0), 1)
                train_ratings.append({
                    "movie_id": m.movie_id,
                    "title": m.title,
                    "rating": score,
                    "timestamp": self.cutoff_ts - rng.randint(1000, 10000000),
                    "genres": m.genres
                })

            # Ground truth: 1-2 cold start movies rated >= 4.0 in test period
            n_cold = rng.randint(1, min(2, len(cold_movies)))
            chosen_cold = rng.sample(cold_movies, n_cold)

            test_ratings: List[Dict[str, Any]] = []
            gt_ids: List[int] = []
            for cm in chosen_cold:
                score = round(rng.uniform(4.0, 5.0), 1)
                test_ratings.append({
                    "movie_id": cm.movie_id,
                    "title": cm.title,
                    "rating": score,
                    "timestamp": self.cutoff_ts + rng.randint(1000, 10000000),
                    "genres": cm.genres
                })
                gt_ids.append(cm.movie_id)

            # Verification: Ground truth NEVER in train history
            train_mids = {r["movie_id"] for r in train_ratings}
            for gid in gt_ids:
                assert gid not in train_mids, f"Data leakage: GT movie {gid} found in user {uid} train history!"

            viewers.append({
                "user_id": uid,
                "train_history": train_ratings,
                "test_ratings": test_ratings,
                "ground_truth_ids": gt_ids
            })

        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(viewers, f, indent=2)

        return viewers

def load_or_create_eval_split(
    path: Optional[Path] = None,
    seed: int = 42
) -> List[Dict[str, Any]]:
    p = path or (PROJECT_ROOT / "demo" / "results" / "eval_viewers.json")
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    builder = EvalSplitBuilder(seed=seed)
    return builder.build_split(output_file=p)

if __name__ == "__main__":
    builder = EvalSplitBuilder(seed=settings.eval_seed if hasattr(settings, "eval_seed") else 42)
    viewers = builder.build_split(output_file=PROJECT_ROOT / "demo" / "results" / "eval_viewers.json")
    print(f"Generated {len(viewers)} deterministic evaluation test viewers.")
