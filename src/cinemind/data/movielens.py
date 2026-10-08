"""MovieLens 32M download and parsing.

Raw files live in data/raw/ (gitignored, never committed: MovieLens license).
"""

import csv
import io
import sys
import urllib.request
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, Optional, Tuple

from src.cinemind.config import PROJECT_ROOT

ML32M_URL = "https://files.grouplens.org/datasets/movielens/ml-32m.zip"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
ZIP_NAME = "ml-32m.zip"
SECONDS_PER_MONTH = 30 * 24 * 3600


class DataBuildError(RuntimeError):
    """Raised for data build problems that should be reported as one line."""


def zip_path(raw_dir: Optional[Path] = None) -> Path:
    return (raw_dir or RAW_DIR) / ZIP_NAME


def download_movielens(raw_dir: Optional[Path] = None, url: str = ML32M_URL) -> Path:
    """Downloads ml-32m.zip into raw_dir unless it is already there."""
    target = zip_path(raw_dir)
    if target.exists():
        print(f"[MovieLens] Using existing {target}")
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".zip.part")
    print(f"[MovieLens] Downloading {url} ...")
    try:
        urllib.request.urlretrieve(url, tmp)
    except Exception as e:
        raise DataBuildError(f"Could not download MovieLens 32M from {url}: {e}") from None
    tmp.rename(target)
    return target


def load_links(zp: Path) -> Dict[int, int]:
    """Returns {movieId: tmdbId} for every movie that has a TMDB link."""
    links: Dict[int, int] = {}
    with zipfile.ZipFile(zp) as zf:
        with zf.open("ml-32m/links.csv") as raw:
            for row in csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8")):
                tmdb = (row.get("tmdbId") or "").strip()
                if tmdb:
                    links[int(row["movieId"])] = int(float(tmdb))
    return links


def iter_ratings(zp: Path) -> Iterator[Tuple[int, int, float, int]]:
    """Streams (userId, movieId, rating, timestamp) from ratings.csv."""
    with zipfile.ZipFile(zp) as zf:
        with zf.open("ml-32m/ratings.csv") as raw:
            raw.readline()  # header
            for line in raw:
                parts = line.rstrip().split(b",")
                if len(parts) >= 4:
                    yield int(parts[0]), int(parts[1]), float(parts[2]), int(parts[3])


@dataclass
class RatingStats:
    max_ts: int
    cutoff_ts: int
    train_counts: Dict[int, int] = field(default_factory=dict)
    test_counts: Dict[int, int] = field(default_factory=dict)
    first_ts: Dict[int, int] = field(default_factory=dict)


def fmt_ts(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def compute_cutoff(max_ts: int, cutoff_months: int) -> int:
    return max_ts - cutoff_months * SECONDS_PER_MONTH


def check_cutoff(min_ts: int, max_ts: int, cutoff_months: int) -> int:
    """Returns cutoff T = max − N months; fails loudly if there is no train period."""
    cutoff = compute_cutoff(max_ts, cutoff_months)
    print(f"[MovieLens] Latest rating timestamp: {max_ts} ({fmt_ts(max_ts)})")
    print(f"[MovieLens] Cutoff T (latest − {cutoff_months} months): {cutoff} ({fmt_ts(cutoff)})")
    if cutoff <= min_ts:
        raise DataBuildError(
            f"Ratings span {fmt_ts(min_ts)}..{fmt_ts(max_ts)}, which is not more than "
            f"{cutoff_months} months; the time-based split needs a train period before the cutoff."
        )
    return cutoff


def compute_rating_stats(zp: Path, cutoff_months: int = 12) -> RatingStats:
    """Two passes: find max timestamp, then count train/test ratings per movie."""
    min_ts, max_ts = sys.maxsize, 0
    for _, _, _, ts in iter_ratings(zp):
        if ts > max_ts:
            max_ts = ts
        if ts < min_ts:
            min_ts = ts
    if max_ts == 0:
        raise DataBuildError(f"No ratings found in {zp}")
    cutoff = check_cutoff(min_ts, max_ts, cutoff_months)

    train: Dict[int, int] = defaultdict(int)
    test: Dict[int, int] = defaultdict(int)
    first: Dict[int, int] = {}
    for _, mid, _, ts in iter_ratings(zp):
        if mid not in first or ts < first[mid]:
            first[mid] = ts
        if ts < cutoff:
            train[mid] += 1
        else:
            test[mid] += 1
    return RatingStats(max_ts=max_ts, cutoff_ts=cutoff, train_counts=dict(train),
                       test_counts=dict(test), first_ts=first)
