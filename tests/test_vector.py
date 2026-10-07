import pytest
from pathlib import Path
from src.cinemind.data.build_catalog import load_catalog
from src.cinemind.retrieval.embed import build_vector_index
from src.cinemind.retrieval.vector import VectorIndex

def test_vector_indexing_and_search(tmp_path: Path):
    persist_dir = tmp_path / "chroma_test"
    catalog = load_catalog()
    assert len(catalog) > 0

    collection = build_vector_index(catalog=catalog, persist_dir=persist_dir)
    assert collection.count() == len(catalog)

    index = VectorIndex(persist_dir=persist_dir)
    assert index.count() == len(catalog)

    # 1. Searching for space exploration and time dilation returns Interstellar (109487)
    results = index.search("space exploration and time dilation wormhole interstellar", k=10)
    result_ids = [mid for mid, _ in results]
    assert 109487 in result_ids

    # 2. Exclude ids are never returned
    excluded_results = index.search(
        "space exploration and time dilation",
        k=10,
        exclude_ids={109487}
    )
    excluded_ids = [mid for mid, _ in excluded_results]
    assert 109487 not in excluded_ids
