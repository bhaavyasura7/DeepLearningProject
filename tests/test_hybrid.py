import pytest
from src.cinemind.data.build_catalog import load_catalog
from src.cinemind.retrieval.hybrid import HybridRetriever

def test_hybrid_retrieval_integrity():
    retriever = HybridRetriever()

    # Query: Inception, seed: Inception (79132)
    # 1. Hybrid mode
    hybrid_res = retriever.retrieve(
        profile_text="Mind-bending science fiction with Nolan themes",
        query="Inception style",
        seed_ids=[79132],
        history_ids={79132},
        config="hybrid"
    )

    assert len(hybrid_res) <= 50
    # Unique ids
    unique_ids = {c.movie_id for c in hybrid_res}
    assert len(unique_ids) == len(hybrid_res)
    # History never in candidate set
    assert 79132 not in unique_ids

    # 2. Vector config never returns graph-only
    vector_res = retriever.retrieve(
        profile_text="Mind-bending science fiction",
        query="",
        seed_ids=[79132],
        history_ids={79132},
        config="vector"
    )
    for c in vector_res:
        assert c.sources == ["vector"]

    # 3. Graph config never returns vector-only
    graph_res = retriever.retrieve(
        profile_text="Mind-bending science fiction",
        query="",
        seed_ids=[79132],
        history_ids={79132},
        config="graph"
    )
    for c in graph_res:
        assert c.sources == ["graph"]
        assert c.path is not None

    # Check that in hybrid, any movie present in both has both sources
    vec_ids = {c.movie_id for c in vector_res}
    graph_ids = {c.movie_id for c in graph_res}
    common = vec_ids.intersection(graph_ids)

    if common:
        for mid in common:
            cand = next(c for c in hybrid_res if c.movie_id == mid)
            assert "vector" in cand.sources
            assert "graph" in cand.sources


def test_query_entities_seed_the_graph():
    retriever = HybridRetriever()
    movies, people = retriever.entities_in_query("smart sci-fi like Inception, ideally by Christopher Nolan")
    assert 79132 in movies                      # Inception
    assert "Christopher Nolan" in people
    assert retriever.entities_in_query("a heartwarming film that will lift me up")[0] == []

    cands = retriever.retrieve(profile_text="cerebral sci-fi", query="something like Inception",
                               seed_ids=[], history_ids=set(), config="graph")
    ids = {c.movie_id for c in cands}
    assert 79132 not in ids                     # the named movie itself is not recommended
    assert any("Christopher Nolan" in (c.path or "") for c in cands)
