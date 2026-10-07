import hashlib
import json
import math
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import chromadb
import httpx
import numpy as np

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

def deterministic_fallback_embedding(text: str, dim: int = 768) -> List[float]:
    """Generates a deterministic normalized unit vector for offline/test environments."""
    words = text.lower().split()
    vec = np.zeros(dim, dtype=np.float32)
    for i, w in enumerate(words):
        h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 8) % 2 == 0) else -1.0
        vec[idx] += sign * (1.0 / (1.0 + math.log1p(i + 1)))
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec.tolist()

class EmbeddingService:
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or settings.ollama_url).rstrip("/")
        self.model = model or settings.embedding_model

    def embed_text(self, text: str) -> List[float]:
        try:
            with httpx.Client(timeout=30.0) as client:
                res = client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text}
                )
                if res.status_code == 200:
                    data = res.json()
                    emb = data.get("embedding")
                    if emb and len(emb) > 0:
                        return emb
        except Exception:
            pass
        return deterministic_fallback_embedding(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]

def build_vector_index(
    catalog: Optional[List[Movie]] = None,
    persist_dir: Optional[Path] = None
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
    embedder = EmbeddingService()

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

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas
    )

    print(f"[Vector] Successfully indexed {collection.count()} movies into Chroma at {p_dir}")
    return collection

if __name__ == "__main__":
    build_vector_index()
