from typing import Optional, List, Tuple
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.movie import Movie


class MovieService:
    @staticmethod
    def get_movies(
        db: Session,
        search: Optional[str] = None,
        genre: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Movie], int]:
        if page < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page must be >= 1")
        if page_size < 1 or page_size > 100:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Page size must be between 1 and 100")

        query = db.query(Movie)

        if search:
            search_clean = f"%{search.strip()}%"
            query = query.filter(Movie.title.ilike(search_clean))

        if genre and genre.strip():
            genre_clean = f"%{genre.strip()}%"
            query = query.filter(Movie.genres.ilike(genre_clean))

        total = query.count()
        movies = (
            query.order_by(Movie.release_year.desc().nullslast(), Movie.title.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return movies, total

    @staticmethod
    def get_movie_by_id(db: Session, movie_id: str) -> Movie:
        movie = db.query(Movie).filter(Movie.id == movie_id).first()
        if not movie:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
        return movie

    @staticmethod
    def get_genres(db: Session) -> List[str]:
        # Collect distinct genres from movies table
        records = db.query(Movie.genres).distinct().all()
        genre_set = set()
        for rec in records:
            if rec[0]:
                for g in rec[0].split("|"):
                    g_clean = g.strip()
                    if g_clean and g_clean != "(no genres listed)":
                        genre_set.add(g_clean)
        return sorted(list(genre_set))
