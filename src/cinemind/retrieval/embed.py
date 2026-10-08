import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import chromadb
import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cinemind.config import settings
from src.cinemind.data.build_catalog import load_catalog
from src.cinemind.schemas import Movie

def format_movie_for_embedding(movie: Movie) -> str:
    genres_str = ", ".join(movie.genres) if movie.genres else "None"
    cast_str = ", ".join(movie.cast[:3]) if movie.cast else ""
    return f"{movie.title} ({movie.year}). {movie.overview} Genres: {genres_str}. Director: {movie.director or 'Unknown'}. Cast: {cast_str}."

class EmbeddingError(RuntimeError):
    """The embedding model could not be reached or returned bad output."""


class EmbeddingService:
    """nomic-embed-text through Ollama (spec Plan: Embeddings)."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or settings.ollama_url).rstrip("/")
        self.model = model or settings.embedding_model

    def embed_text(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str], batch_size: int = 64) -> List[List[float]]:
        out: List[List[float]] = []
        with httpx.Client(timeout=120.0) as client:
            for i in range(0, len(texts), batch_size):
                chunk = texts[i:i + batch_size]
                try:
                    res = client.post(f"{self.base_url}/api/embed", json={"model": self.model, "input": chunk})
                except httpx.HTTPError as e:
                    raise EmbeddingError(
                        f"Ollama not reachable at {self.base_url} ({type(e).__name__}); "
                        f"start it and run `ollama pull {self.model}`."
                    ) from None
                if res.status_code != 200:
                    raise EmbeddingError(f"Ollama /api/embed returned {res.status_code}: {res.text[:200]}")
                embs = res.json().get("embeddings")
                if not embs or len(embs) != len(chunk):
                    raise EmbeddingError("Ollama returned a wrong number of embeddings.")
                out.extend(embs)
                if len(texts) > batch_size:
                    print(f"[Vector] embedded {min(i + batch_size, len(texts))}/{len(texts)}", flush=True)
        return out

def build_vector_index(
    catalog: Optional[List[Movie]] = None,
    persist_dir: Optional[Path] = None,
    embedder: Optional[Any] = None,
) -> chromadb.Collection:
    """Builds and populates the Chroma vector collection from the catalog."""
    p_dir = persist_dir or settings.vector_dir
    p_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(p_dir))
    # Reset or get collection
    try:
        client.delete_collection("cinemind_movies")
    except Exception:
        pass

    collection = client.create_collection(
        name="cinemind_movies",
        metadata={"hnsw:space": "cosine"}
    )

    movies = catalog or load_catalog()
    embedder = embedder or EmbeddingService()

    texts: List[str] = []
    ids: List[str] = []
    metadatas: List[Dict[str, Any]] = []

    for m in movies:
        texts.append(format_movie_for_embedding(m))
        ids.append(str(m.movie_id))
        metadatas.append({
            "movie_id": m.movie_id,
            "title": m.title,
            "year": m.year or 0,
            "director": m.director or "",
            "genres": ", ".join(m.genres)
        })

    print(f"[Vector] Generating embeddings for {len(texts)} catalog movies...")
    embeddings = embedder.embed_batch(texts)

    # Insert in chunks of 2000 to respect Chroma's maximum batch size (5,461)
    chunk_size = 2000
    for i in range(0, len(ids), chunk_size):
        collection.add(
            ids=ids[i:i + chunk_size],
            documents=texts[i:i + chunk_size],
            embeddings=embeddings[i:i + chunk_size],
            metadatas=metadatas[i:i + chunk_size]
        )

    print(f"[Vector] Successfully indexed {collection.count()} movies into Chroma at {p_dir}")
    return collection

if __name__ == "__main__":
    from src.cinemind.data.movielens import DataBuildError
    try:
        build_vector_index()
    except (EmbeddingError, DataBuildError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
