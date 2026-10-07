import sys
from pathlib import Path
from typing import List, Set, Optional, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cinemind.config import settings
from src.cinemind.data.build_catalog import load_catalog
from src.cinemind.retrieval.graph import MovieGraph
from src.cinemind.retrieval.vector import VectorIndex
from src.cinemind.schemas import Candidate, Movie

class HybridRetriever:
    def __init__(
        self,
        vector_index: Optional[VectorIndex] = None,
        graph: Optional[MovieGraph] = None,
        catalog: Optional[List[Movie]] = None
    ):
        self.vector_index = vector_index or VectorIndex()
        self.graph = graph or MovieGraph.load()
        movies = catalog or load_catalog()
        self.catalog_map: Dict[int, Movie] = {m.movie_id: m for m in movies}

    def _populate_candidate_meta(self, cand: Candidate) -> Candidate:
        movie = self.catalog_map.get(cand.movie_id)
        if movie:
            cand.title = movie.title
            cand.year = movie.year
            cand.overview = movie.overview
            cand.genres = movie.genres
            cand.director = movie.director
            cand.cast = movie.cast
        return cand

    def retrieve(
        self,
        profile_text: str,
        query: Optional[str] = None,
        seed_ids: Optional[List[int]] = None,
        history_ids: Optional[Set[int]] = None,
        config: str = "hybrid"
    ) -> List[Candidate]:
        """
        Retrieves candidates according to the requested configuration:
        'vector', 'graph', or 'hybrid'.
        """
        exclude_set = set(history_ids or set())
        seeds = seed_ids or []
        search_query = f"{profile_text} {query or ''}".strip()

        vector_candidates: List[Candidate] = []
        graph_candidates: List[Candidate] = []

        # 1. Vector retrieval
        if config in ("vector", "hybrid"):
            vec_res = self.vector_index.search(
                query=search_query,
                k=settings.vector_top_k,
                exclude_ids=exclude_set
            )
            for mid, score in vec_res:
                c = Candidate(
                    movie_id=mid,
                    sources=["vector"],
                    path=None,
                    score=score
                )
                vector_candidates.append(self._populate_candidate_meta(c))

        # 2. Graph retrieval
        if config in ("graph", "hybrid"):
            graph_res = self.graph.walk(
                seed_movie_ids=seeds,
                k=settings.graph_top_k,
                exclude_ids=exclude_set
            )
            for mid, score, path in graph_res:
                c = Candidate(
                    movie_id=mid,
                    sources=["graph"],
                    path=path,
                    score=score
                )
                graph_candidates.append(self._populate_candidate_meta(c))

        if config == "vector":
            return vector_candidates[:settings.hybrid_cap]

        if config == "graph":
            return graph_candidates[:settings.hybrid_cap]

        # 3. Hybrid: Interleave by rank, union, de-duplicate, keep both source tags, cap at 50
        merged_map: Dict[int, Candidate] = {}
        ordered_ids: List[int] = []

        max_len = max(len(vector_candidates), len(graph_candidates))
        for i in range(max_len):
            # Interleave vector
            if i < len(vector_candidates):
                vc = vector_candidates[i]
                if vc.movie_id not in merged_map:
                    merged_map[vc.movie_id] = vc
                    ordered_ids.append(vc.movie_id)
                else:
                    existing = merged_map[vc.movie_id]
                    if "vector" not in existing.sources:
                        existing.sources.append("vector")

            # Interleave graph
            if i < len(graph_candidates):
                gc = graph_candidates[i]
                if gc.movie_id not in merged_map:
                    merged_map[gc.movie_id] = gc
                    ordered_ids.append(gc.movie_id)
                else:
                    existing = merged_map[gc.movie_id]
                    if "graph" not in existing.sources:
                        existing.sources.append("graph")
                    if not existing.path and gc.path:
                        existing.path = gc.path

        final_candidates: List[Candidate] = []
        for mid in ordered_ids:
            final_candidates.append(merged_map[mid])
            if len(final_candidates) >= settings.hybrid_cap:
                break

        return final_candidates
