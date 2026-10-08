import re
import sys
from pathlib import Path
from typing import List, Set, Optional, Dict, Any, Tuple

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
        self._title_index: Optional[Dict[str, Movie]] = None
        self._people: Set[str] = set()

    def entities_in_query(self, query: Optional[str]) -> Tuple[List[int], List[str]]:
        """Catalog movies and people named in the query (spec: graph seeds).

        Single-word titles must appear with their capitalisation ("Inception")
        and be >= 6 letters, so words like "Up" or "Heat" in a sentence don't match.
        Returns (movie_ids, person_names).
        """
        if not query or not query.strip():
            return [], []
        if self._title_index is None:
            by_title: Dict[str, Movie] = {}
            people: Set[str] = set()
            for m in self.catalog_map.values():
                key = m.title.strip()
                prev = by_title.get(key)
                if prev is None or m.n_ratings_train > prev.n_ratings_train:
                    by_title[key] = m
                if m.director:
                    people.add(m.director)
                people.update(m.cast)
            self._title_index = by_title
            self._people = {p for p in people if len(p.split()) >= 2}
        ql = query.lower()
        movies: List[int] = []
        for title, m in self._title_index.items():
            multi = " " in title
            if (multi and len(title) >= 5 and re.search(rf"(?<!\w){re.escape(title.lower())}(?!\w)", ql)) or \
               (not multi and len(title) >= 6 and re.search(rf"(?<!\w){re.escape(title)}(?!\w)", query)):
                movies.append(m.movie_id)
        names = [p for p in self._people if re.search(rf"(?<!\w){re.escape(p.lower())}(?!\w)", ql)]
        return sorted(movies), sorted(names)

    def _populate_candidate_meta(self, cand: Candidate) -> Candidate:
        movie = self.catalog_map.get(cand.movie_id)
        if movie:
            cand.title = movie.title
            cand.year = movie.year
            cand.overview = movie.overview
            cand.genres = movie.genres
            cand.director = movie.director
            cand.cast = movie.cast
            cand.n_ratings_train = movie.n_ratings_train
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
        named_movies, named_people = self.entities_in_query(query)
        # "like Inception" asks for movies similar to Inception, not Inception itself
        exclude_set = set(history_ids or set()) | set(named_movies)
        seeds = list(dict.fromkeys(list(seed_ids or []) + named_movies))
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
                exclude_ids=exclude_set,
                seed_people=named_people,
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
