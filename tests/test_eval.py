import json
from pathlib import Path

import pytest

from src.cinemind.config import settings
from src.cinemind.data.build_catalog import load_catalog
from src.cinemind.eval.report import generate_report
from src.cinemind.eval.run import run_evaluation
from src.cinemind.llm import LLMClient


def _viewers(n: int):
    """Test viewers over the fixture catalog (test data, not an evaluation split)."""
    movies = sorted(load_catalog(), key=lambda m: m.movie_id)
    warm = [m for m in movies if m.n_ratings_train > 0]
    cold = [m for m in movies if m.n_ratings_train == 0]
    out = []
    for uid in range(1, n + 1):
        hist = warm[uid * 3:uid * 3 + 20]
        out.append({
            "user_id": uid,
            "train_history": [{"movie_id": m.movie_id, "title": m.title, "rating": 4.5,
                               "timestamp": 1_600_000_000 + i, "genres": m.genres}
                              for i, m in enumerate(hist)],
            "ground_truth_ids": [cold[uid % len(cold)].movie_id],
        })
    return out


def _lines(p: Path):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


@pytest.mark.asyncio
async def test_evaluation_resumes_and_matches_uninterrupted_run(tmp_path: Path):
    viewers = _viewers(10)

    settings._raw["data"]["eval_checkpoint_path"] = str(tmp_path / "interrupted.jsonl")
    await run_evaluation(num_viewers=5, configs=["vector"], llm=LLMClient(stub=True), viewers=viewers)
    assert len(_lines(settings.eval_checkpoint_path)) == 5
    await run_evaluation(num_viewers=10, configs=["vector"], llm=LLMClient(stub=True), viewers=viewers)
    interrupted = _lines(settings.eval_checkpoint_path)
    assert [e["user_id"] for e in interrupted] == list(range(1, 11))  # first 5 not redone

    settings._raw["data"]["eval_checkpoint_path"] = str(tmp_path / "full.jsonl")
    await run_evaluation(num_viewers=10, configs=["vector"], llm=LLMClient(stub=True), viewers=viewers)
    full = _lines(settings.eval_checkpoint_path)
    assert [e["recommended_ids"] for e in interrupted] == [e["recommended_ids"] for e in full]


@pytest.mark.asyncio
async def test_report_has_all_configs_and_metrics(tmp_path: Path):
    settings._raw["data"]["eval_checkpoint_path"] = str(tmp_path / "cp.jsonl")
    await run_evaluation(num_viewers=3, llm=LLMClient(stub=True), viewers=_viewers(3))
    generate_report()
    data = json.loads(settings.results_path.read_text())
    for cfg in ("vector", "hybrid", "graph"):
        for key in ("hit_rate_at_5", "hit_rate_at_10", "ndcg_at_5", "ndcg_at_10", "recall_at_50",
                    "avg_llm_calls", "avg_seconds"):
            assert key in data["metrics"][cfg]
    md = (settings.results_path.parent / "results.md").read_text()
    assert "beat similarity-only" in md or "tied similarity-only" in md
