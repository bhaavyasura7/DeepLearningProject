import json
import random
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple, Optional
from src.cinemind.config import settings, PROJECT_ROOT
from src.cinemind.data import movielens
from src.cinemind.data.build_catalog import load_catalog, split_meta_path
from src.cinemind.data.movielens import DataBuildError
from src.cinemind.schemas import Rated, Movie

MAX_HISTORY = 50  # most recent train ratings kept per viewer (understanding uses 30)


def build_movielens_split(
    catalog: List[Movie],
    zip_path: Path,
    cutoff_ts: int,
    seed: int = 42,
    num_viewers: int = 200,
    min_train_ratings: int = 20,
) -> List[Dict[str, Any]]:
    """Real time-based split from MovieLens ratings (spec evaluation protocol).

    Train = ratings before cutoff on catalog movies; ground truth = cold-start
    catalog movies (0 train ratings) the viewer rated >= 4 at/after the cutoff.
    """
    catalog_ids = {m.movie_id for m in catalog}
    cold_ids = {m.movie_id for m in catalog if m.n_ratings_train == 0}
    titles = {m.movie_id: m for m in catalog}

    # Pass 1: train counts and cold-start positives per user
    n_train: Dict[int, int] = {}
    positives: Dict[int, Set[int]] = {}
    for uid, mid, rating, ts in movielens.iter_ratings(zip_path):
        if mid not in catalog_ids:
            continue
        if ts < cutoff_ts:
            n_train[uid] = n_train.get(uid, 0) + 1
        elif mid in cold_ids and rating >= 4.0:
            positives.setdefault(uid, set()).add(mid)

    eligible = sorted(u for u, gt in positives.items() if n_train.get(u, 0) >= min_train_ratings)
    if not eligible:
        raise ValueError("No eligible test viewers (>= 20 train ratings and a cold-start positive).")
    rng = random.Random(seed)
    sampled = sorted(rng.sample(eligible, min(num_viewers, len(eligible))))
    sampled_set = set(sampled)
    print(f"[Split] {len(eligible):,} eligible viewers; sampled {len(sampled)} (seed={seed})")

    # Pass 2: train histories for sampled users
    hist: Dict[int, List[Tuple[int, int, float]]] = {u: [] for u in sampled}
    for uid, mid, rating, ts in movielens.iter_ratings(zip_path):
        if uid in sampled_set and ts < cutoff_ts and mid in catalog_ids:
            hist[uid].append((ts, mid, rating))

    viewers: List[Dict[str, Any]] = []
    for uid in sampled:
        recent = sorted(hist[uid])[-MAX_HISTORY:]
        train = [{"movie_id": mid, "title": titles[mid].title, "rating": r, "timestamp": ts,
                  "genres": titles[mid].genres} for ts, mid, r in recent]
        gt = sorted(positives[uid] - {mid for _, mid, _ in hist[uid]})
        viewers.append({"user_id": uid, "train_history": train, "ground_truth_ids": gt})
    return [v for v in viewers if v["ground_truth_ids"]]


DEFAULT_SPLIT_PATH = PROJECT_ROOT / "demo" / "results" / "eval_viewers.json"


class EvalSplitBuilder:
    """Builds the real MovieLens evaluation split; deterministic for a given seed."""

    def __init__(self, seed: int = 42, raw_dir: Optional[Path] = None, catalog_path: Optional[Path] = None):
        self.seed = seed
        self.raw_dir = raw_dir
        self.catalog_path = catalog_path

    def build_split(self, num_viewers: int = 200, output_file: Optional[Path] = None) -> List[Dict[str, Any]]:
        meta_file = split_meta_path(self.catalog_path)
        zp = movielens.zip_path(self.raw_dir)
        if not meta_file.exists() or not zp.exists():
            raise DataBuildError(
                f"Evaluation needs the MovieLens catalog build ({meta_file}) and ratings ({zp}); run `make data`."
            )
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        viewers = build_movielens_split(
            load_catalog(self.catalog_path), zp, int(meta["cutoff_ts"]), seed=self.seed,
            num_viewers=num_viewers,
            min_train_ratings=int(settings._raw.get("eval", {}).get("min_train_ratings", 20)),
        )
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(viewers, f, indent=2)
        return viewers


def load_or_create_eval_split(path: Optional[Path] = None, seed: Optional[int] = None) -> List[Dict[str, Any]]:
    p = path or DEFAULT_SPLIT_PATH
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    cfg = settings._raw.get("eval", {})
    builder = EvalSplitBuilder(seed=seed if seed is not None else int(cfg.get("seed", 42)))
    return builder.build_split(num_viewers=int(cfg.get("sample_viewers", 200)), output_file=p)


if __name__ == "__main__":  # pragma: no cover
    import sys
    cfg = settings._raw.get("eval", {})
    try:
        viewers = EvalSplitBuilder(seed=int(cfg.get("seed", 42))).build_split(
            num_viewers=int(cfg.get("sample_viewers", 200)), output_file=DEFAULT_SPLIT_PATH)
    except DataBuildError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Wrote {len(viewers)} MovieLens test viewers to {DEFAULT_SPLIT_PATH}")
