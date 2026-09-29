import math
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.movie import MovieResponse, MovieListResponse
from app.services.movie_service import MovieService

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("", response_model=MovieListResponse)
def list_movies(
    search: Optional[str] = Query(None, description="Search term in title"),
    genre: Optional[str] = Query(None, description="Genre filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    items, total = MovieService.get_movies(
        db=db,
        search=search,
        genre=genre,
        page=page,
        page_size=page_size
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return MovieListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/genres", response_model=List[str])
def list_genres(db: Session = Depends(get_db)):
    return MovieService.get_genres(db)


@router.get("/{movie_id}", response_model=MovieResponse)
def get_movie_detail(movie_id: str, db: Session = Depends(get_db)):
    return MovieService.get_movie_by_id(db, movie_id)
