import math
import pickle
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Set, Optional, Any
import networkx as nx

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cinemind.config import settings
from src.cinemind.data.build_catalog import load_catalog
from src.cinemind.schemas import Movie

class MovieGraph:
    def __init__(self, graph: Optional[nx.Graph] = None):
        self.g: nx.Graph = graph if graph is not None else nx.Graph()

    @classmethod
    def build_from_catalog(cls, movies: List[Movie]) -> "MovieGraph":
        g = nx.Graph()

        # Compute genre frequencies
        genre_freq: Dict[str, int] = {}
        for m in movies:
            for genre in m.genres:
                genre_freq[genre] = genre_freq.get(genre, 0) + 1

        for m in movies:
            m_node = f"movie:{m.movie_id}"
            g.add_node(
                m_node,
                type="movie",
                movie_id=m.movie_id,
                title=m.title,
                year=m.year,
                overview=m.overview,
                n_ratings_train=m.n_ratings_train
            )

            # Director (weight 3.0)
            if m.director:
                d_node = f"person:{m.director}"
                if not g.has_node(d_node):
                    g.add_node(d_node, type="person", name=m.director, role="director")
                g.add_edge(m_node, d_node, weight=3.0, relation="directed_by", entity_name=m.director)

            # Cast (weight 2.0)
            for actor in m.cast[:5]:
                a_node = f"person:{actor}"
                if not g.has_node(a_node):
                    g.add_node(a_node, type="person", name=actor, role="cast")
                g.add_edge(m_node, a_node, weight=2.0, relation="starring", entity_name=actor)

            # Keywords (weight 1.5)
            for kw in m.keywords:
                k_node = f"keyword:{kw}"
                if not g.has_node(k_node):
                    g.add_node(k_node, type="keyword", name=kw)
                g.add_edge(m_node, k_node, weight=1.5, relation="has_keyword", entity_name=kw)

            # Genres (weight 1.0 / log(1 + freq))
            for genre in m.genres:
                g_node = f"genre:{genre}"
                freq = genre_freq.get(genre, 1)
                genre_weight = 1.0 / math.log1p(freq)
                if not g.has_node(g_node):
                    g.add_node(g_node, type="genre", name=genre)
                g.add_edge(m_node, g_node, weight=genre_weight, relation="has_genre", entity_name=genre)

        return cls(g)

    def save(self, path: Optional[Path] = None) -> None:
        p = path or settings.graph_path
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            pickle.dump(self.g, f)
        print(f"[Graph] Saved graph with {self.g.number_of_nodes()} nodes and {self.g.number_of_edges()} edges to {p}")

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "MovieGraph":
        p = path or settings.graph_path
        if not p.exists():
            catalog = load_catalog()
            mg = cls.build_from_catalog(catalog)
            mg.save(p)
            return mg
        with open(p, "rb") as f:
            g = pickle.load(f)
        return cls(g)

    def find_best_path(self, seed_nodes: Set[str], target_node: str) -> str:
        """Finds the most descriptive 2-hop connecting chain from seeds to target."""
        best_path_str = ""
        max_edge_prod = -1.0
        target_title = self.g.nodes[target_node].get("title", target_node)

        for seed in seed_nodes:
            seed_title = self.g.nodes[seed].get("title", seed)
            # Check 2-hop neighbors (common entity)
            seed_neighbors = set(self.g.neighbors(seed))
            target_neighbors = set(self.g.neighbors(target_node))
            common_entities = seed_neighbors.intersection(target_neighbors)

            for entity in common_entities:
                w1 = self.g[seed][entity].get("weight", 1.0)
                w2 = self.g[entity][target_node].get("weight", 1.0)
                score = w1 * w2
                if score > max_edge_prod:
                    max_edge_prod = score
                    entity_name = self.g.nodes[entity].get("name", entity.split(":", 1)[-1])
                    rel = self.g[target_node][entity].get("relation", "")
                    if rel == "directed_by":
                        chain = f"{seed_title} → Director: {entity_name} → {target_title}"
                    elif rel == "starring":
                        chain = f"{seed_title} → Cast: {entity_name} → {target_title}"
                    elif rel == "has_keyword":
                        chain = f"{seed_title} → Theme: {entity_name} → {target_title}"
                    else:
                        chain = f"{seed_title} → {entity_name} → {target_title}"
                    best_path_str = chain

        return best_path_str or f"Connected to watched preferences → {target_title}"

    def walk(
        self,
        seed_movie_ids: List[int],
        k: int = 30,
        exclude_ids: Optional[Set[int]] = None
    ) -> List[Tuple[int, float, str]]:
        """
        Executes personalized PageRank restricted to 2-hop neighborhood of seeds.
        Returns list of (movie_id, score, path_description).
        Guarantees seed_movie_ids and exclude_ids are never returned.
        """
        if not seed_movie_ids:
            return []

        exclude_set = set(exclude_ids or set()).union(set(seed_movie_ids))
        seed_nodes = {f"movie:{mid}" for mid in seed_movie_ids if self.g.has_node(f"movie:{mid}")}
        if not seed_nodes:
            return []

        # 2-hop neighborhood expansion
        subgraph_nodes: Set[str] = set(seed_nodes)
        for s in seed_nodes:
            hop1 = set(self.g.neighbors(s))
            subgraph_nodes.update(hop1)
            for h1 in hop1:
                hop2 = set(self.g.neighbors(h1))
                subgraph_nodes.update(hop2)

        sub_g = self.g.subgraph(subgraph_nodes).copy()

        # Personalized PageRank distribution
        personalization = {n: (1.0 / len(seed_nodes)) if n in seed_nodes else 0.0 for n in sub_g.nodes()}

        try:
            ppr = nx.pagerank(
                sub_g,
                alpha=settings.graph_damping,
                personalization=personalization,
                weight="weight",
                max_iter=100
            )
        except Exception:
            # Fallback if convergence issues
            ppr = {n: 0.0 for n in sub_g.nodes()}

        # Filter and rank movies
        candidate_scores: List[Tuple[int, float, str]] = []
        for node, score in ppr.items():
            if not node.startswith("movie:"):
                continue
            try:
                mid = int(node.split(":")[1])
                if mid in exclude_set:
                    continue

                path = self.find_best_path(seed_nodes, node)
                candidate_scores.append((mid, score, path))
            except (ValueError, IndexError):
                continue

        candidate_scores.sort(key=lambda x: x[1], reverse=True)
        return candidate_scores[:k]

if __name__ == "__main__":
    catalog = load_catalog()
    mg = MovieGraph.build_from_catalog(catalog)
    mg.save()
