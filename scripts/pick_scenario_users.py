"""Binds demo scenarios to real MovieLens 32M viewers (`make scenarios`).

For each scenario with a `select` block, finds the real user whose pre-cutoff
ratings best match it and stores that user's actual rating history (most recent
50 train ratings on catalog movies). For cold-start scenarios the user must also
have rated the cold-start `target` >= 4 after the cutoff, so the scenario has a
real ground truth.

  "select": {"liked": [79132, 109487], "target": 287699}

Ranking: number of `liked` movies rated >= 4 before the cutoff, then number of
train ratings, then lowest user id (deterministic).
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cinemind.config import settings
from src.cinemind.data import movielens
from src.cinemind.data.build_catalog import load_catalog, split_meta_path
from src.cinemind.data.movielens import DataBuildError

MAX_HISTORY = 50


def main() -> int:
    try:
        catalog = {m.movie_id: m for m in load_catalog()}
        meta_file = split_meta_path()
        zp = movielens.zip_path()
        if not meta_file.exists() or not zp.exists():
            raise DataBuildError("Needs the MovieLens build; run `make data` first.")
    except DataBuildError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    cutoff = int(json.loads(meta_file.read_text())["cutoff_ts"])

    scenarios = json.loads(settings.scenarios_path.read_text(encoding="utf-8"))
    selecting = [s for s in scenarios if s.get("select")]
    liked_sets = {s["id"]: set(s["select"].get("liked", [])) for s in selecting}
    targets = {s["id"]: s["select"].get("target") for s in selecting}
    watched = set().union(*liked_sets.values()) if liked_sets else set()
    target_ids = {t for t in targets.values() if t}

    print("[Scenarios] Pass 1: scanning ratings for matching viewers...")
    n_train: Dict[int, int] = {}
    liked_by: Dict[int, Set[int]] = {}
    target_pos: Dict[int, Set[int]] = {}
    for uid, mid, rating, ts in movielens.iter_ratings(zp):
        if mid not in catalog:
            continue
        if ts < cutoff:
            n_train[uid] = n_train.get(uid, 0) + 1
            if rating >= 4.0 and mid in watched:
                liked_by.setdefault(uid, set()).add(mid)
        elif rating >= 4.0 and mid in target_ids:
            target_pos.setdefault(uid, set()).add(mid)

    chosen: Dict[str, int] = {}
    for sc in selecting:
        want, target = liked_sets[sc["id"]], targets[sc["id"]]
        best: Tuple = ()
        for uid, liked in liked_by.items():
            if n_train.get(uid, 0) < 20 or uid in chosen.values():
                continue
            if target and target not in target_pos.get(uid, set()):
                continue
            key = (len(liked & want), n_train[uid], -uid)
            if not best or key > best[0]:
                best = (key, uid)
        if not best:
            print(f"ERROR: no real viewer matches scenario {sc['id']}", file=sys.stderr)
            return 1
        chosen[sc["id"]] = best[1]
        print(f"  {sc['id']}: user {best[1]} ({best[0][0]}/{len(want)} liked seeds, {best[0][1]} train ratings)")

    print("[Scenarios] Pass 2: collecting their real histories...")
    users = set(chosen.values())
    hist: Dict[int, List[Tuple[int, int, float]]] = {u: [] for u in users}
    for uid, mid, rating, ts in movielens.iter_ratings(zp):
        if uid in users and ts < cutoff and mid in catalog:
            hist[uid].append((ts, mid, rating))

    for sc in selecting:
        uid = chosen[sc["id"]]
        recent = sorted(hist[uid])[-MAX_HISTORY:]
        sc["user_id"] = uid
        sc["history"] = [{"movie_id": mid, "title": catalog[mid].title, "rating": r, "timestamp": ts,
                          "genres": catalog[mid].genres} for ts, mid, r in recent]
        if targets[sc["id"]]:
            sc["ground_truth_ids"] = sorted(target_pos[uid])
            sc["ground_truth"] = [{"movie_id": m, "title": catalog[m].title, "year": catalog[m].year}
                                  for m in sc["ground_truth_ids"]]

    settings.scenarios_path.write_text(json.dumps(scenarios, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[Scenarios] Updated {settings.scenarios_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
