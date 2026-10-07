import json
import pytest
from pathlib import Path
from src.cinemind.data.build_catalog import build_catalog, load_catalog

def test_catalog_build_integrity(tmp_path: Path):
    cat_file = tmp_path / "catalog.jsonl"
    movies = build_catalog(output_path=cat_file)

    assert len(movies) > 0
    cold_start_count = 0

    for m in movies:
        assert m.overview and len(m.overview.strip()) > 0
        assert m.director and len(m.director.strip()) > 0
        assert m.cast and len(m.cast) >= 1
        if m.n_ratings_train == 0:
            cold_start_count += 1

    assert cold_start_count > 0

def test_catalog_determinism(tmp_path: Path):
    path1 = tmp_path / "catalog1.jsonl"
    path2 = tmp_path / "catalog2.jsonl"

    build_catalog(output_path=path1)
    build_catalog(output_path=path2)

    with open(path1, "rb") as f1, open(path2, "rb") as f2:
        assert f1.read() == f2.read()
