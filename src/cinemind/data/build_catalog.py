"""Catalog build (`make data`) and loading.

Full build (MovieLens 32M present or downloadable):
  catalog = movies with >= 50 train ratings
          ∪ movies first rated at/after cutoff T with >= 3 test ratings,
  where T = latest rating − 12 months. Movies without an overview, director or
  cast are dropped. Writes data/processed/catalog.jsonl and split_meta.json.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cinemind.config import settings
from src.cinemind.data import movielens, tmdb
from src.cinemind.data.movielens import DataBuildError
from src.cinemind.schemas import Movie

_eval_cfg = settings._raw.get("eval", {})
CUTOFF_MONTHS = int(_eval_cfg.get("cutoff_months", 12))
MIN_TRAIN = int(_eval_cfg.get("min_catalog_train_ratings", 50))
MIN_TEST_COLD = int(_eval_cfg.get("min_test_ratings_cold", 3))

_cache: Dict[Tuple[str, float], List[Movie]] = {}


def split_meta_path(catalog_path: Optional[Path] = None) -> Path:
    return (catalog_path or settings.catalog_path).parent / "split_meta.json"


def _read_jsonl(path: Path) -> List[Movie]:
    with open(path, "r", encoding="utf-8") as f:
        return [Movie.model_validate_json(line) for line in f if line.strip()]


class CatalogMissing(DataBuildError):
    """The catalog has not been built yet."""


def load_catalog(path: Optional[Path] = None) -> List[Movie]:
    """Loads the catalog built by `make data`."""
    p = path or settings.catalog_path
    if not p.exists():
        raise CatalogMissing(f"Catalog not found at {p}; run `make data` first.")
    key = (str(p), p.stat().st_mtime)
    if key not in _cache:
        _cache[key] = _read_jsonl(p)
    return list(_cache[key])


def write_catalog(movies: List[Movie], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for m in sorted(movies, key=lambda m: m.movie_id):
            f.write(m.model_dump_json() + "\n")


def print_stats(movies: List[Movie], dropped: int = 0, label: str = "Catalog") -> None:
    n = len(movies) or 1
    n_cold = sum(1 for m in movies if m.n_ratings_train == 0)
    print("=" * 60)
    print(f" {label}")
    print("=" * 60)
    print(f"Movies:               {len(movies):,}")
    print(f"Cold-start (0 train): {n_cold:,}")
    print(f"With director:        {100 * sum(1 for m in movies if m.director) / n:.1f}%")
    print(f"With cast >= 1:       {100 * sum(1 for m in movies if m.cast) / n:.1f}%")
    if dropped:
        print(f"Dropped (no overview/director/cast): {dropped:,}")
    print("=" * 60)


def build_from_movielens(
    raw_dir: Optional[Path] = None,
    output_path: Optional[Path] = None,
    download: bool = True,
) -> List[Movie]:
    out = output_path or settings.catalog_path
    zp = movielens.download_movielens(raw_dir) if download else movielens.zip_path(raw_dir)
    if not zp.exists():
        raise DataBuildError(f"MovieLens archive not found at {zp}")

    stats = movielens.compute_rating_stats(zp, CUTOFF_MONTHS)
    links = movielens.load_links(zp)

    eligible: List[int] = []
    for mid in sorted(links):
        n_train = stats.train_counts.get(mid, 0)
        is_warm = n_train >= MIN_TRAIN
        is_cold = (n_train == 0 and stats.first_ts.get(mid, 0) >= stats.cutoff_ts
                   and stats.test_counts.get(mid, 0) >= MIN_TEST_COLD)
        if is_warm or is_cold:
            eligible.append(mid)
    print(f"[Catalog] {len(eligible):,} movies pass the rating rule")

    csv_path = (raw_dir or movielens.RAW_DIR) / tmdb.TMDB_CSV.name
    if csv_path.exists():
        print(f"[TMDB] Using local dump {csv_path}")
        meta = tmdb.load_csv(csv_path)
    else:
        meta = tmdb.fetch_missing([links[m] for m in eligible])

    movies: List[Movie] = []
    dropped = 0
    for mid in eligible:
        rec = meta.get(links[mid])
        if not rec or rec.get("missing") or not rec.get("overview") or not rec.get("director") or not rec.get("cast"):
            dropped += 1
            continue
        date = rec.get("release_date") or ""
        movies.append(Movie(
            movie_id=mid,
            tmdb_id=links[mid],
            title=rec["title"],
            year=int(date[:4]) if date[:4].isdigit() else None,
            genres=rec.get("genres") or [],
            overview=rec["overview"],
            director=rec["director"],
            cast=rec["cast"][:5],
            keywords=rec.get("keywords") or [],
            poster_path=rec.get("poster_path"),
            first_rating_ts=stats.first_ts.get(mid),
            n_ratings_train=stats.train_counts.get(mid, 0),
        ))

    if not any(m.n_ratings_train == 0 for m in movies):
        raise DataBuildError("Catalog has no cold-start movies; check the cutoff and data.")

    write_catalog(movies, out)
    split_meta_path(out).write_text(json.dumps({
        "max_ts": stats.max_ts, "cutoff_ts": stats.cutoff_ts, "cutoff_months": CUTOFF_MONTHS,
        "source": "movielens-32m",
    }, indent=2), encoding="utf-8")
    print_stats(movies, dropped, "MovieLens 32M + TMDB catalog")
    return sorted(movies, key=lambda m: m.movie_id)


def build_catalog(
    output_path: Optional[Path] = None,
    raw_dir: Optional[Path] = None,
    download: bool = True,
) -> List[Movie]:
    return build_from_movielens(raw_dir=raw_dir, output_path=output_path, download=download)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the CineMind catalog.")
    parser.add_argument("--no-download", action="store_true",
                        help="Use data/raw/ml-32m.zip only; do not download it.")
    args = parser.parse_args()
    try:
        build_catalog(download=not args.no_download)
    except DataBuildError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
