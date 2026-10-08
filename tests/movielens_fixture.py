"""Builds a tiny MovieLens-format archive + TMDB CSV for exercising the real ingest code."""

import csv
import io
import zipfile
from pathlib import Path

DAY = 86400
T0 = 1_500_000_000  # ratings start here
SPAN_DAYS = 800      # > 12 months, so a train period exists

# movieId: (tmdbId, title, date, director, cast, has_overview)
MOVIES = {
    1: (101, "Old Classic", "1990-01-01", "Ann Director", "A One, A Two", True),
    2: (102, "Old Thriller", "1995-05-05", "Ann Director", "B One", True),
    3: (103, "Mid Drama", "2005-03-03", "Bob Director", "C One", True),
    4: (104, "No Overview Film", "2001-01-01", "Bob Director", "D One", False),
    5: (105, "Brand New", "2023-01-01", "Ann Director", "A One", True),
    6: (106, "Brand New Two", "2023-02-02", "Bob Director", "C One", True),
    7: (107, "Rare Film", "1999-09-09", "Cy Director", "E One", True),
}


def rating_rows():
    cutoff_day = SPAN_DAYS - 365
    rows = []
    for uid in range(1, 81):
        # train: everyone rates 1, 2, 3, 4 before the cutoff (>= 50 train ratings each movie)
        for i, mid in enumerate((1, 2, 3, 4)):
            rows.append((uid, mid, 4.5 if uid % 2 else 3.0, T0 + (10 + i + uid) * DAY))
        # extra train ratings so viewers have >= 20
        for j in range(20):
            rows.append((uid, (1, 2, 3)[j % 3], 4.0, T0 + (50 + j) * DAY))
        # test period: new movies first rated after the cutoff
        if uid <= 40:
            rows.append((uid, 5, 5.0 if uid % 2 else 2.0, T0 + (cutoff_day + 30 + uid) * DAY))
        if uid <= 10:
            rows.append((uid, 6, 4.0, T0 + (cutoff_day + 60) * DAY))
    rows.append((1, 7, 4.0, T0 + 5 * DAY))           # rare film: 1 train rating -> excluded
    rows.append((2, 1, 4.0, T0 + SPAN_DAYS * DAY))   # latest timestamp
    return sorted(rows, key=lambda r: (r[3], r[0], r[1]))


def write_fixture(raw_dir: Path) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    zp = raw_dir / "ml-32m.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        links = io.StringIO()
        w = csv.writer(links)
        w.writerow(["movieId", "imdbId", "tmdbId"])
        for mid, m in MOVIES.items():
            w.writerow([mid, f"tt{mid:07d}", m[0]])
        zf.writestr("ml-32m/links.csv", links.getvalue())
        ratings = io.StringIO()
        w = csv.writer(ratings)
        w.writerow(["userId", "movieId", "rating", "timestamp"])
        for r in rating_rows():
            w.writerow(r)
        zf.writestr("ml-32m/ratings.csv", ratings.getvalue())

    with open(raw_dir / "tmdb_movies_full.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "title", "release_date", "overview", "genres", "directors", "cast", "keywords", "poster_path"])
        for mid, (tid, title, date, director, cast, has_ov) in MOVIES.items():
            ov = f"{title} is a film. It has a plot about things." if has_ov else ""
            w.writerow([tid, title, date, ov, "Drama, Thriller", director, cast, "twist, heist", ""])
    return zp
