from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class MovieResponse(BaseModel):
    id: str
    movielens_id: int
    title: str
    release_year: Optional[int] = None
    genres: str
    metadata_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class MovieListResponse(BaseModel):
    items: List[MovieResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
