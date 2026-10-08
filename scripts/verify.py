"""`make verify`: checks the automatable acceptance criteria from spec.md against
the real built data, the recorded traces and the real model. Exits 0 only if all pass.

Needs: `make data index` done, Ollama running with the configured model, `make record` done.
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from httpx import ASGITransport, AsyncClient

from src.cinemind.agents.guards import extract_evidence_quote
from src.cinemind.config import settings
from src.cinemind.data.build_catalog import load_catalog
from src.cinemind.data.movielens import DataBuildError
from src.cinemind.eval.split import EvalSplitBuilder
from src.cinemind.llm import LLMClient
from src.cinemind.pipeline import Pipeline
from src.cinemind.retrieval.vector import VectorIndex
from src.cinemind.schemas import Rated, RecommendRequest, Trace
from src.cinemind.trace import TraceManager

results: List[Tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    color = "\033[92m" if passed else "\033[91m"
    print(f"[{color}{'PASS' if passed else 'FAIL'}\033[0m] {name}{f' ({detail})' if detail else ''}")
    results.append((name, passed, detail))


def check_trace(trace: Trace, catalog_map: dict, history_ids: set) -> Tuple[bool, str]:
    cand = {c.movie_id for c in trace.candidates}
    ids = [f.movie_id for f in trace.final]
    if len(ids) != settings.final_k:
        return False, f"{len(ids)} results"
    if not set(ids) <= cand:
        return False, "result outside candidate set"
    if set(ids) & history_ids:
        return False, "result in history"
    for f in trace.final:
        if not (f.reason and f.quote and (f.path or f.sources)):
            return False, f"{f.movie_id} missing reason/quote/discovery"
        if f.quote not in catalog_map[f.movie_id].overview:
            return False, f"quote for {f.movie_id} not a substring"
    return True, ", ".join(catalog_map[i].title for i in ids)


async def main() -> int:
    print("=" * 60 + "\n CineMind acceptance verification\n" + "=" * 60)
    try:
        catalog = load_catalog()
    except DataBuildError as e:
        print(f"ERROR: {e}")
        return 1
    cmap = {m.movie_id: m for m in catalog}
    scenarios = json.loads(settings.scenarios_path.read_text(encoding="utf-8"))

    n_cold = sum(1 for m in catalog if m.n_ratings_train == 0)
    check("Catalog: overview/director/cast on every movie, cold-start > 0",
          all(m.overview and m.director and m.cast for m in catalog) and n_cold > 0,
          f"{len(catalog)} movies, {n_cold} cold-start")
    check("Vector index count equals catalog", VectorIndex().count() == len(catalog))
    check("Quotes are exact substrings (all movies)",
          all(extract_evidence_quote(m.overview, "story about love and war") in m.overview for m in catalog))

    # Split determinism + leakage (real MovieLens split)
    try:
        b = EvalSplitBuilder(seed=int(settings._raw.get("eval", {}).get("seed", 42)))
        tmp = settings.results_path.parent
        p1, p2 = tmp / ".verify_split1.json", tmp / ".verify_split2.json"
        v1 = b.build_split(num_viewers=50, output_file=p1)
        b.build_split(num_viewers=50, output_file=p2)
        same = p1.read_bytes() == p2.read_bytes()
        leak = any(set(v["ground_truth_ids"]) & {h["movie_id"] for h in v["train_history"]} for v in v1)
        p1.unlink(), p2.unlink()
        check("Split byte-identical across runs and leak-free", same and not leak, f"{len(v1)} viewers")
    except DataBuildError as e:
        check("Split byte-identical across runs and leak-free", False, str(e))

    # Replay: every scenario has both traces, renders < 1 s with 0 model calls
    tm = TraceManager()
    from src.cinemind.server import app
    probe = LLMClient(stub=False)
    calls0 = probe.call_count
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        for sc in scenarios:
            for cfg in ("vector", "hybrid"):
                tr = tm.get_scenario_trace(sc["id"], cfg)
                if tr is None:
                    check(f"Replay {sc['id']}/{cfg}", False, "no trace; run `make record`")
                    continue
                t0 = time.time()
                res = await client.post("/api/recommend", json={"mode": sc["mode"], "query": sc.get("query"),
                                        "replay": True, "scenario_id": sc["id"], "retrieval": cfg})
                body = res.text
                dur = time.time() - t0 - 0.08 * len(tr.stages)  # minus the UI pacing sleeps
                ok, detail = check_trace(tr, cmap, {h["movie_id"] for h in sc.get("history") or []})
                check(f"Replay {sc['id']}/{cfg}", res.status_code == 200 and "final" in body and dur < 1.0 and ok,
                      detail)
                if sc.get("cold_start") and cfg == "hybrid":
                    cold = [cmap[f.movie_id].title for f in tr.final if cmap[f.movie_id].n_ratings_train == 0]
                    check(f"Cold-start movie in {sc['id']} hybrid results", bool(cold), ", ".join(cold) or "none")
        check("Replay made no model calls", probe.call_count == calls0)
        res = await client.post("/api/recommend", json={"mode": "query", "query": "", "history": []})
        check("Empty query + empty history rejected with 400", res.status_code == 400)

    # Live smoke run on 2 scenarios against the real model
    llm = LLMClient(stub=False)
    if not await llm.ping():
        check("Live smoke run", False, f"model server not reachable at {settings.ollama_url}")
    else:
        pipe = Pipeline(llm=llm)
        req = RecommendRequest(mode="query", query="fun sci-fi like Inception but shorter", retrieval="hybrid")
        tr = await pipe.run(req)
        ok, detail = check_trace(tr, cmap, set())
        check("Live: 'fun sci-fi like Inception but shorter' → 5 explained results", ok,
              f"{detail} · {tr.metrics.get('seconds')}s, {tr.metrics.get('llm_calls')} calls")
        feed = next((s for s in scenarios if s["mode"] == "feed" and s.get("history")), None)
        if feed:
            hist = [Rated(**h) for h in feed["history"]]
            tr = await pipe.run(RecommendRequest(mode="feed", history=hist, retrieval="hybrid"))
            ok, detail = check_trace(tr, cmap, {h.movie_id for h in hist})
            check(f"Live feed ({feed['id']}): 5 results, none in history", ok, detail)

    failed = [r for r in results if not r[1]]
    print("=" * 60)
    print(f"{'FAILED' if failed else 'PASSED'}: {len(results) - len(failed)}/{len(results)} checks")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
