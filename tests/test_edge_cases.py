import json

import pytest

from src.cinemind.agents.guards import Guards, extract_evidence_quote, split_into_sentences
from src.cinemind.data.build_catalog import build_catalog
from src.cinemind.data.movielens import DataBuildError
from src.cinemind.eval.metrics import hit_rate_at_k, ndcg_at_k, recall_at_k
from src.cinemind.eval.split import EvalSplitBuilder, load_or_create_eval_split
from src.cinemind.schemas import Candidate, RankedOutputItem, Verdict
from tests.movielens_fixture import write_fixture


def test_quote_edge_cases():
    assert extract_evidence_quote("", "anything") == ""
    ov = "First part here. Second part about dragons."
    assert extract_evidence_quote(ov, "!!") == "First part here."          # no usable words → first sentence
    assert extract_evidence_quote(ov, "dragons everywhere") == "Second part about dragons."
    assert split_into_sentences("   ") == []
    assert split_into_sentences("Dr. No meets Mr. Big. Then chaos.") == ["Dr. No meets Mr. Big.", "Then chaos."]


def test_guards_drop_history_and_duplicates():
    cands = [Candidate(movie_id=i, overview=f"Movie {i} plot.") for i in (1, 2, 3, 4, 5, 6)]
    verdicts = [Verdict(movie_id=i, match=True, fit=1 - i / 10, reason="ok") for i in (1, 2, 3, 4, 5, 6)]
    ranked = [RankedOutputItem(movie_id=m, reason="r") for m in (1, 1, 2, 999, 3)]
    out = Guards.apply_guards(rankings=ranked, candidates=cands, verdicts=verdicts, history_ids={2}, k=5)
    ids = [r.movie_id for r in out]
    assert len(ids) == 5 and len(set(ids)) == 5
    assert 2 not in ids and 999 not in ids
    assert ids[:2] == [1, 3]


def test_metrics_empty_inputs():
    assert hit_rate_at_k([1, 2], [], k=5) == 0.0
    assert ndcg_at_k([1, 2], [], k=5) == 0.0
    assert ndcg_at_k([], [1], k=5) == 0.0
    assert recall_at_k([1], [], k=50) == 0.0
    assert ndcg_at_k([9, 1], [1], k=5) == pytest.approx(1 / 1.5849625, rel=1e-6)


def test_split_requires_real_data(tmp_path):
    with pytest.raises(DataBuildError, match="make data"):
        EvalSplitBuilder(raw_dir=tmp_path, catalog_path=tmp_path / "catalog.jsonl").build_split(num_viewers=5)


def test_load_or_create_reads_existing_split(tmp_path):
    p = tmp_path / "viewers.json"
    p.write_text(json.dumps([{"user_id": 7, "train_history": [], "ground_truth_ids": [1]}]))
    assert load_or_create_eval_split(path=p)[0]["user_id"] == 7


def test_split_with_no_eligible_viewers(tmp_path):
    raw = tmp_path / "raw"
    write_fixture(raw)
    cat = tmp_path / "catalog.jsonl"
    build_catalog(output_path=cat, raw_dir=raw, download=False)
    from src.cinemind.data import movielens
    from src.cinemind.data.build_catalog import load_catalog
    from src.cinemind.eval.split import build_movielens_split
    meta = json.loads((tmp_path / "split_meta.json").read_text())
    with pytest.raises(ValueError, match="No eligible"):
        build_movielens_split(load_catalog(cat), movielens.zip_path(raw), meta["cutoff_ts"], min_train_ratings=10_000)


def test_load_or_create_builds_when_missing(tmp_path):
    # no MovieLens build in the test environment → clear error instead of an invented split
    with pytest.raises(DataBuildError):
        load_or_create_eval_split(path=tmp_path / "missing.json")
