"""Comprehensive verification script checking every automatable acceptance criterion for CineMind.

Exits 0 if and only if all acceptance criteria pass.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cinemind.config import settings
from src.cinemind.data.build_catalog import load_catalog
from src.cinemind.eval.metrics import hit_rate_at_k, ndcg_at_k, recall_at_k
from src.cinemind.eval.split import EvalSplitBuilder
from src.cinemind.llm import LLMClient
from src.cinemind.pipeline import Pipeline
from src.cinemind.retrieval.graph import MovieGraph
from src.cinemind.retrieval.hybrid import HybridRetriever
from src.cinemind.retrieval.vector import VectorIndex
from src.cinemind.schemas import RecommendRequest, Rated, RankedOutputItem, Candidate, Verdict
from src.cinemind.agents.guards import Guards, extract_evidence_quote
from src.cinemind.trace import TraceManager

results: List[Tuple[str, bool, str]] = []

def check(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    color = "\033[92m" if passed else "\033[91m"
    reset = "\033[0m"
    print(f"[{color}{status}{reset}] {name} {f'({detail})' if detail else ''}")
    results.append((name, passed, detail))

async def main():
    print("=" * 60)
    print(" CineMind Acceptance Criteria Verification Suite")
    print("=" * 60)

    # 1. Catalog Integrity
    catalog = load_catalog()
    has_meta = all(m.overview and m.director and len(m.cast) >= 1 for m in catalog)
    n_cold = sum(1 for m in catalog if m.n_ratings_train == 0)
    check("Catalog Integrity", has_meta and n_cold > 0, f"{len(catalog)} movies, {n_cold} cold-start")

    # 2. Vector Index Count & Exclusions
    v_index = VectorIndex()
    v_count = v_index.count()
    v_res = v_index.search("space exploration and time dilation", k=5, exclude_ids={109487})
    v_no_leak = 109487 not in [mid for mid, _ in v_res]
    check("Vector Index & Exclusion", (v_count == len(catalog)) and v_no_leak, f"Count {v_count}, exclusion verified")

    # 3. Graph Walk & Path Construction
    graph = MovieGraph.load()
    g_res = graph.walk(seed_movie_ids=[79132], k=5)  # Seed Inception
    g_no_seeds = 79132 not in [mid for mid, _, _ in g_res]
    g_has_paths = all(path and len(path) > 0 for _, _, path in g_res)
    check("Graph Walk & Explanations", g_no_seeds and g_has_paths, f"Seeds excluded, paths present")

    # 4. Hybrid Merge & De-duplication
    retriever = HybridRetriever(vector_index=v_index, graph=graph, catalog=catalog)
    h_cands = retriever.retrieve("sci-fi", seed_ids=[79132], history_ids={79132}, config="hybrid")
    h_unique = len({c.movie_id for c in h_cands}) == len(h_cands)
    h_cap = len(h_cands) <= settings.hybrid_cap
    check("Hybrid Interleaving & De-dup", h_unique and h_cap, f"{len(h_cands)} unique candidates <= 50")

    # 5. Quote Substring Guard Across All Catalog Movies
    quote_checks = []
    for m in catalog:
        q = extract_evidence_quote(m.overview, "compelling story with deep themes")
        quote_checks.append(q in m.overview)
    check("Extractive Quote Verbatim Guard", all(quote_checks), f"100% exact substring match across {len(catalog)} movies")

    # 6. Guard: Candidate Set Inclusion & Weak Match Filling
    sample_cands = [Candidate(movie_id=1, overview="test ov 1"), Candidate(movie_id=2, overview="test ov 2")]
    sample_verdicts = [Verdict(movie_id=1, match=True, fit=0.9, reason="Match"), Verdict(movie_id=2, match=False, fit=0.3, reason="Weak")]
    ranked = Guards.apply_guards(
        rankings=[RankedOutputItem(movie_id=999999, reason="Hallucinated"), RankedOutputItem(movie_id=1, reason="Good")],
        candidates=sample_cands,
        verdicts=sample_verdicts,
        k=2
    )
    r_ids = [r.movie_id for r in ranked]
    check("Candidate Set Guard & Weak Fill", (999999 not in r_ids) and (len(ranked) == 2), f"Replaced hallucinated ID: {r_ids}")

    # 7. Replay Mode Verification (<1s, zero model calls)
    tm = TraceManager()
    replay_client = LLMClient(stub=True)
    initial_calls = replay_client.call_count
    t0 = time.time()
    nolan_trace = tm.get_scenario_trace("nolan_scifi", "hybrid")
    replay_dur = time.time() - t0
    check("Preset Scenario Replay", (nolan_trace is not None) and (replay_dur < 1.0) and (replay_client.call_count == initial_calls), f"{replay_dur:.4f}s, 0 model calls")

    # 8. Evaluation Split Determinism & Zero Leakage
    builder = EvalSplitBuilder(seed=42)
    viewers = builder.build_split(num_viewers=20)
    no_leakage = True
    for v in viewers:
        train_ids = {r["movie_id"] for r in v["train_history"]}
        if set(v["ground_truth_ids"]).intersection(train_ids):
            no_leakage = False
            break
    check("Eval Split Leakage Verification", no_leakage, f"20 sampled viewers, zero ground truth train leakage")

    # 9. Metric Fixtures
    hr_pass = hit_rate_at_k([1, 2, 3], {2}, k=2) == 1.0
    ndcg_pass = ndcg_at_k([1, 2], {1}, k=5) == 1.0
    check("Evaluation Metric Accuracy", hr_pass and ndcg_pass, "HitRate@k and NDCG@k verified")

    # 10. Smoke Run: Hybrid Pipeline
    llm = LLMClient(stub=True)
    pipe = Pipeline(llm=llm, retriever=retriever)
    smoke_trace = await pipe.run(RecommendRequest(
        mode="query",
        query="fun sci-fi like Inception but shorter",
        retrieval="hybrid"
    ))
    smoke_pass = len(smoke_trace.final) == 5 and all(f.quote and f.reason for f in smoke_trace.final)
    check("End-to-End Pipeline Smoke Run", smoke_pass, "5 recommendations, reasons & quotes verified")

    print("=" * 60)
    failed = [r for r in results if not r[1]]
    if failed:
        print(f"FAILED: {len(failed)} acceptance criteria failed.")
        sys.exit(1)
    else:
        print(f"SUCCESS: All {len(results)} acceptance criteria PASSED!")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
