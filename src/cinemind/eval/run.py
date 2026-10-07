import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Set, Tuple, Dict, Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cinemind.config import settings
from src.cinemind.eval.split import load_or_create_eval_split
from src.cinemind.llm import LLMClient
from src.cinemind.pipeline import Pipeline
from src.cinemind.schemas import RecommendRequest, Rated, Trace

async def run_evaluation(
    num_viewers: int = 200,
    configs: Optional[List[str]] = None,
    use_live: bool = False
):
    eval_configs = configs or ["vector", "graph", "hybrid"]
    checkpoint_file = settings.eval_checkpoint_path
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

    # 1. Load completed checkpoints
    completed_pairs: Set[Tuple[int, str]] = set()
    if checkpoint_file.exists():
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        completed_pairs.add((record["user_id"], record["config"]))
                    except Exception:
                        continue

    print(f"[Eval] Loaded {len(completed_pairs)} previously completed (user_id, config) evaluation pairs.")

    viewers = load_or_create_eval_split()[:num_viewers]
    total_pairs = len(viewers) * len(eval_configs)
    print(f"[Eval] Target: {len(viewers)} viewers × {len(eval_configs)} configs = {total_pairs} pairs.")

    llm = LLMClient(stub=not use_live)
    pipeline = Pipeline(llm=llm)

    processed_count = 0
    with open(checkpoint_file, "a", encoding="utf-8") as out_f:
        for v in viewers:
            uid = v["user_id"]
            history = [Rated(**h) for h in v["train_history"]]
            gt_ids = v["ground_truth_ids"]

            for cfg in eval_configs:
                if (uid, cfg) in completed_pairs:
                    continue

                t0 = time.time()
                req = RecommendRequest(
                    mode="feed",
                    user_id=uid,
                    history=history,
                    retrieval=cfg
                )

                trace: Trace = await pipeline.run(req)
                dur = time.time() - t0

                rec_ids = [item.movie_id for item in trace.final]
                cand_ids = [c.movie_id for c in trace.candidates]
                llm_calls = trace.metrics.get("llm_calls", 0)

                checkpoint_entry = {
                    "user_id": uid,
                    "config": cfg,
                    "ground_truth_ids": gt_ids,
                    "recommended_ids": rec_ids,
                    "candidate_ids": cand_ids,
                    "llm_calls": llm_calls,
                    "seconds": dur,
                    "timestamp": time.time()
                }

                out_f.write(json.dumps(checkpoint_entry) + "\n")
                out_f.flush()
                completed_pairs.add((uid, cfg))
                processed_count += 1

                if processed_count % 25 == 0 or processed_count == total_pairs:
                    print(f"[Eval Progress] Completed {len(completed_pairs)}/{total_pairs} pairs...")

    print(f"[Eval] Evaluation run complete! Checkpoints recorded in {checkpoint_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--viewers", type=int, default=200, help="Number of viewers to evaluate")
    parser.add_argument("--live", action="store_true", help="Use live Ollama server calls")
    args = parser.parse_args()
    asyncio.run(run_evaluation(num_viewers=args.viewers, use_live=args.live))
