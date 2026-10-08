"""MovieLens 32M and TMDB Catalog Ingestion Pipeline.

Streams MovieLens 32M ratings (32,000,204 ratings across 87,585 movies) and links,
joins with TMDB dataset metadata, and builds an expanded production catalog (8k-12k movies) per spec.md.
"""

import csv
import json
import os
import sys
import time
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cinemind.config import settings
from src.cinemind.schemas import Movie

SECONDS_PER_YEAR = 365 * 24 * 3600

def parse_list_str(val: str) -> List[str]:
    if not val:
        return []
    return [x.strip() for x in val.split(",") if x.strip()]

def build_ml32m_catalog(
    raw_dir: Optional[Path] = None,
    output_path: Optional[Path] = None,
    min_train_ratings: int = 25,
    max_catalog_size: int = 12000
) -> List[Movie]:
    r_dir = raw_dir or (PROJECT_ROOT / "data" / "raw")
    out_file = output_path or settings.catalog_path
    zip_path = r_dir / "ml-32m.zip"
    tmdb_file = r_dir / "tmdb_movies_full.csv"

    if not zip_path.exists():
        raise FileNotFoundError(f"MovieLens 32M zip archive not found at {zip_path}")
    if not tmdb_file.exists():
        raise FileNotFoundError(f"TMDB dataset not found at {tmdb_file}")

    print("============================================================")
    print(" MovieLens 32M + TMDB Catalog Builder")
    print("============================================================")

    # 1. Read links.csv from ml-32m.zip
    t0 = time.time()
    print("[1/4] Reading MovieLens 32M links...")
    links_tmdb_to_ml: Dict[int, int] = {}
    with zipfile.ZipFile(zip_path, "r") as zf:
        with zf.open("ml-32m/links.csv") as lf:
            lines = lf.read().decode("utf-8").splitlines()
            reader = csv.DictReader(lines)
            for row in reader:
                try:
                    mid = int(row["movieId"])
                    if row.get("tmdbId") and row["tmdbId"].strip():
                        tid = int(row["tmdbId"])
                        links_tmdb_to_ml[tid] = mid
                except (ValueError, KeyError):
                    pass
    print(f"      Loaded {len(links_tmdb_to_ml):,} MovieLens 32M links in {time.time() - t0:.2f}s")

    # 2. Stream ratings.csv from ml-32m.zip in a single fast pass
    t1 = time.time()
    print("[2/4] Streaming 32,000,204 MovieLens ratings...")
    train_counts: Dict[int, int] = defaultdict(int)
    test_counts: Dict[int, int] = defaultdict(int)
    first_ts: Dict[int, int] = {}
    
    # Official GroupLens ML-32M generation date: Oct 13, 2023. Cutoff T = Oct 12, 2022
    cutoff_ts = 1665532800
    
    processed_ratings = 0
    with zipfile.ZipFile(zip_path, "r") as zf:
        with zf.open("ml-32m/ratings.csv") as rf:
            rf.readline()  # header
            for line in rf:
                parts = line.strip().split(b",")
                if len(parts) >= 4:
                    mid = int(parts[1])
                    ts = int(parts[3])
                    if mid not in first_ts or ts < first_ts[mid]:
                        first_ts[mid] = ts
                    if ts < cutoff_ts:
                        train_counts[mid] += 1
                    else:
                        test_counts[mid] += 1
                processed_ratings += 1
                if processed_ratings % 10_000_000 == 0:
                    print(f"      Streamed {processed_ratings // 1_000_000}M / 32M ratings...")

    print(f"      Finished streaming {processed_ratings:,} ratings in {time.time() - t1:.2f}s.")
    print(f"      Distinct movies with ratings: {len(first_ts):,}")

    # 3. Join with TMDB dataset
    t2 = time.time()
    print("[3/4] Joining with TMDB metadata (overviews, cast, crew, keywords)...")
    train_movies: List[Movie] = []
    cold_movies: List[Movie] = []
    seen_mids: Set[int] = set()

    with open(tmdb_file, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                tid = int(row.get("id", 0))
            except ValueError:
                continue

            mid = links_tmdb_to_ml.get(tid)
            n_train = train_counts.get(mid, 0) if mid else 0
            n_test = test_counts.get(mid, 0) if mid else 0

            title = row.get("title", "").strip()
            overview = row.get("overview", "").strip()
            directors_raw = row.get("directors", "").strip()
            cast_raw = row.get("cast", "").strip()
            genres_raw = row.get("genres", "").strip()
            keywords_raw = row.get("keywords", "").strip()
            poster_path = row.get("poster_path", "").strip() or None
            rel_date = row.get("release_date", "").strip()
            vote_count = int(row.get("vote_count") or 0)

            # Metadata integrity check
            if not title or not overview or not directors_raw or not cast_raw:
                continue

            # Spec criteria:
            # - Train movie: has >= min_train_ratings
            # - Cold-start movie: 0 train ratings, released >= 2017 or has test ratings
            is_train = (n_train >= min_train_ratings)
            is_cold = (n_train == 0) and (n_test >= 1 or rel_date >= "2017-01-01" or vote_count >= 100)

            if not (is_train or is_cold):
                continue

            final_mid = mid if mid else (300000 + tid)
            if final_mid in seen_mids:
                continue
            seen_mids.add(final_mid)

            year = int(rel_date[:4]) if (rel_date and len(rel_date) >= 4 and rel_date[:4].isdigit()) else None
            directors = parse_list_str(directors_raw)
            primary_director = directors[0] if directors else "Unknown"
            cast_list = parse_list_str(cast_raw)[:5]
            genres_list = parse_list_str(genres_raw)
            keywords_list = parse_list_str(keywords_raw)[:8]

            movie = Movie(
                movie_id=final_mid,
                tmdb_id=tid,
                title=title,
                year=year,
                genres=genres_list,
                overview=overview,
                director=primary_director,
                cast=cast_list,
                keywords=keywords_list,
                poster_path=poster_path,
                first_rating_ts=first_ts.get(final_mid),
                n_ratings_train=n_train if not is_cold else 0
            )

            if is_train:
                train_movies.append(movie)
            else:
                cold_movies.append(movie)

    # Select movies up to max_catalog_size
    # Sort train movies by rating frequency descending
    train_movies.sort(key=lambda m: m.n_ratings_train, reverse=True)
    # Sort cold movies by year/relevance
    cold_movies.sort(key=lambda m: (m.year or 0), reverse=True)

    target_train = min(len(train_movies), max_catalog_size - min(1500, len(cold_movies)))
    target_cold = min(len(cold_movies), max_catalog_size - target_train)

    combined = train_movies[:target_train] + cold_movies[:target_cold]
    combined.sort(key=lambda m: m.movie_id)

    # 4. Save to catalog.jsonl
    print("[4/4] Writing catalog to disk...")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        for m in combined:
            f.write(m.model_dump_json() + "\n")

    n_total = len(combined)
    n_cold = sum(1 for m in combined if m.n_ratings_train == 0)
    n_train = n_total - n_cold
    pct_dir = (sum(1 for m in combined if m.director) / n_total) * 100
    pct_cast = (sum(1 for m in combined if m.cast) / n_total) * 100

    print("============================================================")
    print(" MovieLens 32M Catalog Build Results")
    print("============================================================")
    print(f"Total Movies:            {n_total:,}")
    print(f"Train Movies (>= {min_train_ratings} rtg): {n_train:,} ({(n_train/n_total)*100:.1f}%)")
    print(f"Cold-Start Movies:       {n_cold:,} ({(n_cold/n_total)*100:.1f}%)")
    print(f"Movies with Director:    {pct_dir:.1f}%")
    print(f"Movies with Cast >= 1:   {pct_cast:.1f}%")
    print(f"Catalog Location:        {out_file}")
    print("============================================================\n")

    return combined

if __name__ == "__main__":
    build_ml32m_catalog()
