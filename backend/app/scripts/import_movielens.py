import argparse
import csv
import logging
import os
import re
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.database import SessionLocal
from app.models.movie import Movie

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("import_movielens")


def parse_title_and_year(raw_title: str):
    """Extract release year from title like 'Toy Story (1995)' -> ('Toy Story', 1995)"""
    match = re.search(r"\((\d{4})\)\s*$", raw_title.strip())
    if match:
        year = int(match.group(1))
        clean_title = raw_title[: match.start()].strip()
        return clean_title, year
    return raw_title.strip(), None


def import_movies(csv_path: str, limit: int = None) -> dict:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"MovieLens CSV not found at: {csv_path}")

    db = SessionLocal()
    summary = {
        "total_rows": 0,
        "accepted": 0,
        "rejected": 0,
        "duplicates_skipped": 0,
    }

    try:
        existing_ids = {m[0] for m in db.query(Movie.movielens_id).all()}

        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            batch = []

            for row in reader:
                summary["total_rows"] += 1
                if limit and summary["accepted"] >= limit:
                    break

                try:
                    movie_id_str = row.get("movieId")
                    raw_title = row.get("title")
                    genres = row.get("genres", "")

                    if not movie_id_str or not raw_title:
                        summary["rejected"] += 1
                        continue

                    ml_id = int(movie_id_str)
                    if ml_id in existing_ids:
                        summary["duplicates_skipped"] += 1
                        continue

                    clean_title, year = parse_title_and_year(raw_title)

                    movie = Movie(
                        movielens_id=ml_id,
                        title=clean_title or raw_title,
                        release_year=year,
                        genres=genres if genres != "(no genres listed)" else "",
                        metadata_json={
                            "original_title": raw_title,
                            "dataset": "MovieLens ml-latest-small"
                        }
                    )
                    batch.append(movie)
                    existing_ids.add(ml_id)
                    summary["accepted"] += 1

                    if len(batch) >= 1000:
                        db.bulk_save_objects(batch)
                        db.commit()
                        batch.clear()
                        logger.info(f"Imported {summary['accepted']} movies...")

                except Exception as row_err:
                    logger.warning(f"Error parsing row {row}: {row_err}")
                    summary["rejected"] += 1

            if batch:
                db.bulk_save_objects(batch)
                db.commit()

        logger.info(f"Import finished successfully. Summary: {summary}")
        return summary
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import MovieLens catalogue into database")
    parser.add_argument("--csv_path", default="data/raw/ml-latest-small/movies.csv", help="Path to movies.csv")
    parser.add_argument("--limit", type=int, default=None, help="Optional maximum rows to import")
    args = parser.parse_args()

    res = import_movies(args.csv_path, args.limit)
    print(res)
