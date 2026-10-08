"""Candidate-set Recall@50 for all three configs over ALL eligible viewers.

No language-model calls: the vector query is built directly from the viewer's
liked movies (titles + genres) and embedded with the embedding model; the graph
is seeded with the 20 most recent movies rated >= 4 (same as the pipeline).
Writes demo/results/recall.json, which `make eval` folds into the report.
"""

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cinemind.config import settings
from src.cinemind.data import movielens
from src.cinemind.data.build_catalog import load_catalog, split_meta_path
from src.cinemind.data.movielens import DataBuildError
from src.cinemind.eval.metrics import recall_at_k
from src.cinemind.eval.split import build_movielens_split
from src.cinemind.retrieval.hybrid import HybridRetriever

RECALL_PATH = PROJECT_ROOT / "demo" / "results" / "recall.json"
CONFIGS = ["vector", "hybrid", "graph"]


def profile_text_from_history(history: List[dict]) -> str:
    liked = sorted((h for h in history if h["rating"] >= 4.0), key=lambda h: h["timestamp"], reverse=True)[:20]
    genres = Counter(g for h in liked for g in (h.get("genres") or []))
    titles = ", ".join(h["title"] for h in liked[:10])
    top = ", ".join(g for g, _ in genres.most_common(4))
    return f"Viewer who loved {titles}. Favourite genres: {top}."


def compute_recall(retriever: HybridRetriever, viewers: List[dict], k: int = 50) -> Dict[str, dict]:
    sums = {c: 0.0 for c in CONFIGS}
    for i, v in enumerate(viewers, 1):
        hist = v["train_history"]
        liked = sorted((h for h in hist if h["rating"] >= 4.0), key=lambda h: h["timestamp"], reverse=True)
        text = profile_text_from_history(hist)
        for cfg in CONFIGS:
            cands = retriever.retrieve(profile_text=text, query=None,
                                       seed_ids=[h["movie_id"] for h in liked[:20]],
                                       history_ids={h["movie_id"] for h in hist}, config=cfg)
            sums[cfg] += recall_at_k([c.movie_id for c in cands], v["ground_truth_ids"], k=k)
        if i % 200 == 0:
            print(f"[Recall] {i}/{len(viewers)} viewers", flush=True)
    n = max(len(viewers), 1)
    return {c: {"recall_at_50": round(sums[c] / n, 4), "viewers": len(viewers)} for c in CONFIGS}


def main() -> int:
    try:
        meta_file, zp = split_meta_path(), movielens.zip_path()
        if not meta_file.exists() or not zp.exists():
            raise DataBuildError("Needs the MovieLens build; run `make data` first.")
        cutoff = int(json.loads(meta_file.read_text())["cutoff_ts"])
        cfg = settings._raw.get("eval", {})
        viewers = build_movielens_split(load_catalog(), zp, cutoff, seed=int(cfg.get("seed", 42)),
                                        num_viewers=10**9,
                                        min_train_ratings=int(cfg.get("min_train_ratings", 20)))
        result = compute_recall(HybridRetriever(), viewers)
    except DataBuildError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    RECALL_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECALL_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
