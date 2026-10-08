import sys
from pathlib import Path
from typing import Any, List, Tuple, Optional, Set
import chromadb

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cinemind.config import settings
from src.cinemind.retrieval.embed import EmbeddingService

class VectorIndex:
    def __init__(self, persist_dir: Optional[Path] = None, embedder: Optional[Any] = None):
        self.persist_dir = persist_dir or settings.vector_dir
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(
            name="cinemind_movies",
            metadata={"hnsw:space": "cosine"}
        )
        self.embedder = embedder or EmbeddingService()

    def count(self) -> int:
        return self.collection.count()

    def search(
        self,
        query: str,
        k: int = 30,
        exclude_ids: Optional[Set[int]] = None
    ) -> List[Tuple[int, float]]:
        """
        Searches Chroma for top movies matching query.
        Returns list of (movie_id, similarity_score).
        Guarantees movies in exclude_ids are never returned.
        """
        exclude_set = exclude_ids or set()
        if not query.strip():
            return []

        query_embedding = self.embedder.embed_text(query)
        # Fetch slightly more to account for excluded items
        fetch_k = min(self.collection.count(), k + len(exclude_set) + 10)
        if fetch_k == 0:
            return []

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch_k,
            include=["metadatas", "distances"]
        )

        candidates: List[Tuple[int, float]] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return []

        ids = results["ids"][0]
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)

        for mid_str, dist in zip(ids, distances):
            try:
                mid = int(mid_str)
                if mid in exclude_set:
                    continue
                # Cosine distance to similarity: similarity = 1.0 - (dist / 2.0) or 1.0 - dist
                sim = max(0.0, min(1.0, 1.0 - float(dist)))
                candidates.append((mid, sim))
                if len(candidates) >= k:
                    break
            except (ValueError, TypeError):
                continue

        return candidates
