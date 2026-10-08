"""Records execution traces for all preset scenarios in both vector and hybrid configurations.

Usage:
    python scripts/record_traces.py    # runs every scenario against the real model (Ollama)
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cinemind.config import settings
from src.cinemind.data.build_catalog import load_catalog
from src.cinemind.llm import LLMClient
from src.cinemind.pipeline import Pipeline
from src.cinemind.schemas import RecommendRequest, Rated, Trace
from src.cinemind.trace import TraceManager

async def record_all_traces():
    scenarios_path = settings.scenarios_path
    if not scenarios_path.exists():
        raise FileNotFoundError(f"Scenarios file not found at {scenarios_path}")

    with open(scenarios_path, "r", encoding="utf-8") as f:
        scenarios: List[Dict[str, Any]] = json.load(f)

    tm = TraceManager()
    catalog = load_catalog()
    catalog_map = {m.movie_id: m for m in catalog}

    llm = LLMClient(stub=False)
    if not await llm.ping():
        raise SystemExit(f"ERROR: model server not reachable at {settings.ollama_url}; "
                         f"recording needs the real model `{settings.llm_model}`.")
    print(f"[Record] Model: {settings.llm_model}")
    pipeline = Pipeline(llm=llm)

    for sc in scenarios:
        sc_id = sc["id"]
        title = sc["title"]
        print(f"\n--- Recording Scenario: {title} ({sc_id}) ---")

        history = [Rated(**h) for h in sc.get("history", [])]
        query = sc.get("query")

        for config in ["vector", "hybrid"]:
            t0 = time.time()
            req = RecommendRequest(
                mode=sc["mode"],
                query=query,
                history=history,
                retrieval=config,
                scenario_id=sc_id
            )

            trace: Trace = await pipeline.run(req)

            # Ensure metadata on final items
            for item in trace.final:
                m = catalog_map.get(item.movie_id)
                if m:
                    item.poster_path = m.poster_path
                    item.title = m.title
                    item.year = m.year
                    item.overview = m.overview

            if sc.get("cold_start"):
                cold = [i.title for i in trace.final
                        if catalog_map.get(i.movie_id) and catalog_map[i.movie_id].n_ratings_train == 0]
                print(f"  [{config}] cold-start movies in final: {cold or 'none'}")

            out_filename = f"{sc_id}_{config}.json"
            out_path = tm.save_trace(trace, filename=out_filename)
            print(f"  Saved {out_filename} ({len(trace.final)} items, {round(time.time() - t0, 2)}s)")

    print("\n[Record] Finished recording all preset scenario traces successfully!")

if __name__ == "__main__":
    asyncio.run(record_all_traces())
