from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class Rated(BaseModel):
    movie_id: int
    title: Optional[str] = None
    rating: float
    timestamp: Optional[int] = None
    genres: Optional[List[str]] = None

class Profile(BaseModel):
    likes: List[str] = Field(default_factory=list, description="Themes, directors, or tropes the user likes")
    dislikes: List[str] = Field(default_factory=list, description="Disliked elements or tropes")
    constraints: List[str] = Field(default_factory=list, description="Explicit constraints e.g. runtime, genre exclusions")
    mood: Optional[str] = Field(default=None, description="Current emotional or stylistic intent")
    summary: str = Field(..., description="Dense 1-2 sentence semantic summary of user preference")

class Candidate(BaseModel):
    movie_id: int
    title: Optional[str] = None
    year: Optional[int] = None
    sources: List[str] = Field(default_factory=list, description="List containing 'vector', 'graph', or both")
    path: Optional[str] = Field(default=None, description="Readable graph path chain if discovered via graph")
    score: float = Field(default=0.0, description="Retrieval ranking score")
    overview: Optional[str] = None
    genres: Optional[List[str]] = None
    director: Optional[str] = None
    cast: Optional[List[str]] = None

class Verdict(BaseModel):
    movie_id: int
    match: bool = Field(..., description="Whether the movie matches the user profile and constraints")
    fit: float = Field(..., ge=0.0, le=1.0, description="Fit score from 0.0 to 1.0")
    reason: str = Field(..., description="One-line justification of the fit")

class JudgeBatchOutput(BaseModel):
    verdicts: List[Verdict]

class Brief(BaseModel):
    strong: List[str] = Field(default_factory=list, description="Top standout recommendations that align best")
    violations: List[str] = Field(default_factory=list, description="Notable discarded movies that failed constraints")
    notes: str = Field(default="", description="Summary note describing the candidate landscape")

class RankedOutputItem(BaseModel):
    movie_id: int
    reason: str

class RankModelOutput(BaseModel):
    rankings: List[RankedOutputItem]

class RankedItem(BaseModel):
    movie_id: int
    rank: int
    title: Optional[str] = None
    year: Optional[int] = None
    reason: str
    path: Optional[str] = None
    quote: Optional[str] = None
    poster_path: Optional[str] = None
    overview: Optional[str] = None
    is_weak_match: bool = False
    sources: List[str] = Field(default_factory=list)
    fit: Optional[float] = None

class StageRecord(BaseModel):
    name: str
    started: float
    ended: float
    status: str = "completed"  # "started", "completed", "failed", "fallback"
    fallback_used: bool = False
    output: Any = None
    error: Optional[str] = None

class Trace(BaseModel):
    run_id: str
    mode: str
    input: Dict[str, Any]
    config: str  # "vector" | "graph" | "hybrid"
    stages: List[StageRecord] = Field(default_factory=list)
    candidates: List[Candidate] = Field(default_factory=list)
    final: List[RankedItem] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)  # llm_calls, seconds

class Movie(BaseModel):
    movie_id: int
    tmdb_id: Optional[int] = None
    title: str
    year: Optional[int] = None
    genres: List[str] = Field(default_factory=list)
    overview: str
    director: Optional[str] = None
    cast: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    poster_path: Optional[str] = None
    first_rating_ts: Optional[int] = None
    n_ratings_train: int = 0

class Scenario(BaseModel):
    id: str
    title: str
    mode: str  # "query" | "feed"
    blurb: str
    cold_start: bool
    query: Optional[str] = None
    user_id: Optional[int] = None
    history: Optional[List[Rated]] = None

class RecommendRequest(BaseModel):
    mode: str = "query"  # "query" | "feed"
    query: Optional[str] = None
    user_id: Optional[int] = None
    history: Optional[List[Rated]] = None
    retrieval: str = "hybrid"  # "vector" | "graph" | "hybrid"
    replay: bool = False
    scenario_id: Optional[str] = None

class HealthResponse(BaseModel):
    model_ready: bool
    catalog_size: int
    graph_ready: bool
    model_name: str
