import csv
import json
import os
from collections import defaultdict
from typing import Dict, List, Tuple, Any


def create_time_aware_split(
    ratings_csv: str = "data/raw/ml-latest-small/ratings.csv",
    output_dir: str = "data/processed",
    min_interactions_per_user: int = 15,
    train_ratio: float = 0.75,
    seed: int = 42
) -> Dict[str, Any]:
    if not os.path.exists(ratings_csv):
        raise FileNotFoundError(f"Ratings CSV not found at {ratings_csv}")

    os.makedirs(output_dir, exist_ok=True)
    user_ratings = defaultdict(list)

    with open(ratings_csv, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            user_ratings[int(row["userId"])].append({
                "movieId": int(row["movieId"]),
                "rating": float(row["rating"]),
                "timestamp": int(row["timestamp"])
            })

    total_raw_users = len(user_ratings)
    eligible_users = {
        uid: ratings for uid, ratings in user_ratings.items()
        if len(ratings) >= min_interactions_per_user
    }

    train_data: Dict[int, List[dict]] = {}
    test_data: Dict[int, List[dict]] = {}

    for uid, ratings in eligible_users.items():
        # Strict chronological sort to prevent future leakage
        sorted_ratings = sorted(ratings, key=lambda x: x["timestamp"])
        split_idx = int(len(sorted_ratings) * train_ratio)
        train_data[uid] = sorted_ratings[:split_idx]
        test_data[uid] = sorted_ratings[split_idx:]

    manifest = {
        "dataset": "MovieLens ml-latest-small",
        "random_seed": seed,
        "min_interactions_per_user": min_interactions_per_user,
        "train_ratio": train_ratio,
        "total_raw_users": total_raw_users,
        "eligible_users_count": len(eligible_users),
        "total_train_interactions": sum(len(v) for v in train_data.values()),
        "total_test_interactions": sum(len(v) for v in test_data.values()),
        "created_at": "2026-09-29T17:40:00Z"
    }

    output_path = os.path.join(output_dir, "time_split.json")
    with open(output_path, "w", encoding="utf-8") as out_f:
        json.dump({
            "manifest": manifest,
            "train": train_data,
            "test": test_data
        }, out_f, indent=2)

    manifest_path = os.path.join(output_dir, "split_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as man_f:
        json.dump(manifest, man_f, indent=2)

    print(f"Time-aware split created successfully at {output_path}")
    print(f"Summary: {manifest}")
    return manifest


if __name__ == "__main__":
    create_time_aware_split()
