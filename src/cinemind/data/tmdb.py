"""TMDB metadata fetcher (resumable) and local-CSV loader.

Each fetched movie is cached as one line in data/raw/tmdb.jsonl, so an
interrupted run only fetches the ids that are still missing.
"""

import csv
import json
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import httpx

from src.cinemind.config import settings
from src.cinemind.data.movielens import RAW_DIR, DataBuildError

TMDB_API = "https://api.themoviedb.org/3"
TMDB_CACHE = RAW_DIR / "tmdb.jsonl"
TMDB_CSV = RAW_DIR / "tmdb_movies_full.csv"


class TMDBKeyError(DataBuildError):
    """Missing or rejected TMDB API key."""


def _split_list(val: str) -> List[str]:
    return [x.strip() for x in (val or "").split(",") if x.strip()]


def parse_tmdb_details(data: dict) -> dict:
    """Flattens a /movie/{id}?append_to_response=credits,keywords response."""
    credits = data.get("credits") or {}
    directors = [c["name"] for c in credits.get("crew", []) if c.get("job") == "Director"]
    cast = [c["name"] for c in sorted(credits.get("cast", []), key=lambda c: c.get("order", 999))]
    kw_block = data.get("keywords") or {}
    keywords = [k["name"] for k in kw_block.get("keywords", kw_block.get("results", []))]
    return {
        "tmdb_id": data["id"],
        "title": (data.get("title") or "").strip(),
        "release_date": data.get("release_date") or "",
        "overview": (data.get("overview") or "").strip(),
        "genres": [g["name"] for g in data.get("genres", [])],
        "director": directors[0] if directors else None,
        "cast": cast[:5],
        "keywords": keywords[:8],
        "poster_path": data.get("poster_path"),
    }


def load_cache(path: Path = TMDB_CACHE) -> Dict[int, dict]:
    cache: Dict[int, dict] = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rec = json.loads(line)
                        cache[int(rec["tmdb_id"])] = rec
                    except (ValueError, KeyError):
                        continue  # torn last line from an interrupted run
    return cache


def load_csv(path: Path = TMDB_CSV) -> Dict[int, dict]:
    """Loads a pre-downloaded TMDB dump (e.g. the Kaggle 'TMDB movies' CSV)."""
    out: Dict[int, dict] = {}
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for row in csv.DictReader(f):
            try:
                tid = int(row.get("id") or 0)
            except ValueError:
                continue
            directors = _split_list(row.get("directors", ""))
            out[tid] = {
                "tmdb_id": tid,
                "title": (row.get("title") or "").strip(),
                "release_date": (row.get("release_date") or "").strip(),
                "overview": (row.get("overview") or "").strip(),
                "genres": _split_list(row.get("genres", "")),
                "director": directors[0] if directors else None,
                "cast": _split_list(row.get("cast", ""))[:5],
                "keywords": _split_list(row.get("keywords", ""))[:8],
                "poster_path": (row.get("poster_path") or "").strip() or None,
            }
    return out


def fetch_missing(
    tmdb_ids: Iterable[int],
    api_key: Optional[str] = None,
    cache_path: Path = TMDB_CACHE,
    delay_s: float = 0.03,
) -> Dict[int, dict]:
    """Fetches metadata for ids not yet cached; returns the full cache."""
    cache = load_cache(cache_path)
    missing = sorted(set(tmdb_ids) - set(cache))
    if not missing:
        return cache
    key = api_key or settings.tmdb_api_key
    if not key:
        raise TMDBKeyError("TMDB_API_KEY is not set; add it to .env (see .env.example).")

    print(f"[TMDB] {len(cache)} cached, fetching {len(missing)} missing ids...")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=20.0) as client, open(cache_path, "a", encoding="utf-8") as out:
        for i, tid in enumerate(missing, 1):
            try:
                res = client.get(f"{TMDB_API}/movie/{tid}",
                                 params={"api_key": key, "append_to_response": "credits,keywords"})
            except httpx.HTTPError as e:
                raise DataBuildError(f"TMDB request failed: {type(e).__name__}") from None
            if res.status_code == 401:
                raise TMDBKeyError("TMDB rejected the API key (401); check TMDB_API_KEY in .env.")
            if res.status_code == 429:
                time.sleep(2.0)
                continue  # picked up on the next run
            if res.status_code == 404:
                rec = {"tmdb_id": tid, "missing": True}
            elif res.status_code != 200:
                continue
            else:
                rec = parse_tmdb_details(res.json())
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()
            cache[tid] = rec
            if i % 500 == 0:
                print(f"[TMDB] {i}/{len(missing)}")
            time.sleep(delay_s)
    return cache
