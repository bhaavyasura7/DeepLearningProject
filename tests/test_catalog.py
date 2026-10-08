import pytest
from src.cinemind.data import movielens
from src.cinemind.data.build_catalog import build_catalog, load_catalog, split_meta_path
from src.cinemind.data.movielens import DataBuildError
from tests.movielens_fixture import write_fixture


def test_catalog_build_applies_spec_rule(tmp_path):
    raw = tmp_path / "raw"
    write_fixture(raw)
    out = tmp_path / "processed" / "catalog.jsonl"
    movies = build_catalog(output_path=out, raw_dir=raw, download=False)
    ids = {m.movie_id for m in movies}

    assert ids == {1, 2, 3, 5, 6}          # 4 has no overview, 7 too few ratings
    for m in movies:
        assert m.overview.strip() and m.director and m.cast
    cold = {m.movie_id for m in movies if m.n_ratings_train == 0}
    assert cold == {5, 6}
    assert split_meta_path(out).exists()
    assert {m.movie_id for m in load_catalog(out)} == ids


def test_catalog_build_is_deterministic(tmp_path):
    raw = tmp_path / "raw"
    write_fixture(raw)
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    build_catalog(output_path=a, raw_dir=raw, download=False)
    build_catalog(output_path=b, raw_dir=raw, download=False)
    assert a.read_bytes() == b.read_bytes()


def test_cutoff_check_fails_loudly_on_short_data():
    with pytest.raises(DataBuildError, match="not more than 12 months"):
        movielens.check_cutoff(1_600_000_000, 1_600_000_000 + 100 * 86400, 12)


def test_missing_catalog_is_a_clear_error(tmp_path):
    with pytest.raises(DataBuildError, match="make data"):
        load_catalog(tmp_path / "nope.jsonl")
