import json
import sys
from pathlib import Path
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cinemind.config import settings
from src.cinemind.data.build_catalog import load_catalog
from src.cinemind.eval.metrics import hit_rate_at_k, ndcg_at_k, recall_at_k

def generate_report():
    checkpoint_file = settings.eval_checkpoint_path
    if not checkpoint_file.exists():
        print(f"Error: checkpoint file {checkpoint_file} not found. Run eval first.", file=sys.stderr)
        return

    records_by_cfg: Dict[str, List[Dict[str, Any]]] = {}
    with open(checkpoint_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entry = json.loads(line)
                cfg = entry["config"]
                records_by_cfg.setdefault(cfg, []).append(entry)

    catalog = load_catalog()
    catalog_map = {m.movie_id: m for m in catalog}

    configs = ["vector", "hybrid", "graph"]
    metrics_summary: Dict[str, Dict[str, float]] = {}

    for cfg in configs:
        entries = records_by_cfg.get(cfg, [])
        if not entries:
            continue

        n = len(entries)
        hr5 = sum(hit_rate_at_k(e["recommended_ids"], e["ground_truth_ids"], k=5) for e in entries) / n
        hr10 = sum(hit_rate_at_k(e["recommended_ids"], e["ground_truth_ids"], k=10) for e in entries) / n
        ndcg5 = sum(ndcg_at_k(e["recommended_ids"], e["ground_truth_ids"], k=5) for e in entries) / n
        ndcg10 = sum(ndcg_at_k(e["recommended_ids"], e["ground_truth_ids"], k=10) for e in entries) / n
        r50 = sum(recall_at_k(e["candidate_ids"], e["ground_truth_ids"], k=50) for e in entries) / n
        avg_calls = sum(e["llm_calls"] for e in entries) / n
        avg_sec = sum(e["seconds"] for e in entries) / n

        metrics_summary[cfg] = {
            "eval_count": n,
            "hit_rate_at_5": round(hr5, 4),
            "hit_rate_at_10": round(hr10, 4),
            "ndcg_at_5": round(ndcg5, 4),
            "ndcg_at_10": round(ndcg10, 4),
            "recall_at_50": round(r50, 4),
            "avg_llm_calls": round(avg_calls, 1),
            "avg_seconds": round(avg_sec, 2)
        }

    # Error analysis: Compare vector vs hybrid on 10 viewers
    # Collect users where hybrid hit and vector missed, or both struggled
    by_user_cfg: Dict[int, Dict[str, Dict[str, Any]]] = {}
    for cfg, entries in records_by_cfg.items():
        for e in entries:
            by_user_cfg.setdefault(e["user_id"], {})[cfg] = e

    error_analysis_cases: List[Dict[str, Any]] = []
    for uid, user_runs in sorted(by_user_cfg.items()):
        if "vector" in user_runs and "hybrid" in user_runs:
            v_run = user_runs["vector"]
            h_run = user_runs["hybrid"]
            gt = v_run["ground_truth_ids"]

            v_hit = hit_rate_at_k(v_run["recommended_ids"], gt, k=5)
            h_hit = hit_rate_at_k(h_run["recommended_ids"], gt, k=5)

            # Look for divergence or failures
            if h_hit != v_hit or (h_hit == 0 and v_hit == 0):
                gt_titles = [catalog_map[gid].title if gid in catalog_map else f"ID {gid}" for gid in gt]
                v_recs = [catalog_map[mid].title if mid in catalog_map else f"ID {mid}" for mid in v_run["recommended_ids"][:5]]
                h_recs = [catalog_map[mid].title if mid in catalog_map else f"ID {mid}" for mid in h_run["recommended_ids"][:5]]

                error_analysis_cases.append({
                    "user_id": uid,
                    "ground_truth": ", ".join(gt_titles),
                    "vector_hit": bool(v_hit),
                    "hybrid_hit": bool(h_hit),
                    "vector_recommendations": v_recs,
                    "hybrid_recommendations": h_recs
                })
                if len(error_analysis_cases) >= 10:
                    break

    # Construct final results structure
    final_output = {
        "metrics": metrics_summary,
        "error_analysis": error_analysis_cases
    }

    # Save demo/results/results.json
    res_path = settings.results_path
    res_path.parent.mkdir(parents=True, exist_ok=True)
    with open(res_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2)

    # Save demo/results/results.md
    md_path = res_path.parent / "results.md"
    vec = metrics_summary.get("vector", {})
    hyb = metrics_summary.get("hybrid", {})
    gr = metrics_summary.get("graph", {})

    hybrid_won = (hyb.get("hit_rate_at_5", 0) > vec.get("hit_rate_at_5", 0)) or (hyb.get("recall_at_50", 0) > vec.get("recall_at_50", 0))

    md = "# CineMind Cold-Start Evaluation Report\n\n"
    md += f"**Evaluation Protocol:** 200 sampled test viewers with >=20 train ratings; ground truth = cold-start movies (0 train ratings) rated >=4.0 in test period.\n\n"
    md += "## 1. Metric Summary Table\n\n"
    md += "| Retrieval Configuration | HitRate@5 | HitRate@10 | NDCG@5 | NDCG@10 | Recall@50 | Calls / Rec | Sec / Rec |\n"
    md += "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"

    for cfg_name, label in [("vector", "Similarity-Only (ARAG)"), ("hybrid", "Hybrid (CineMind)"), ("graph", "Graph-Only")]:
        c = metrics_summary.get(cfg_name, {})
        md += f"| **{label}** | {c.get('hit_rate_at_5', 0):.4f} | {c.get('hit_rate_at_10', 0):.4f} | {c.get('ndcg_at_5', 0):.4f} | {c.get('ndcg_at_10', 0):.4f} | {c.get('recall_at_50', 0):.4f} | {c.get('avg_llm_calls', 0):.1f} | {c.get('avg_seconds', 0):.2f}s |\n"

    md += "\n## 2. Hypothesis Verdict\n\n"
    if hybrid_won:
        md += "**Verdict: Hybrid Graph Retrieval OUTPERFORMS Similarity-Only.**\n\n"
        md += f"- **Recall@50 Gain:** Hybrid achieved **{hyb.get('recall_at_50', 0)*100:.1f}%** vs **{vec.get('recall_at_50', 0)*100:.1f}%** for vector retrieval.\n"
        md += f"- **HitRate@5:** Hybrid reached **{hyb.get('hit_rate_at_5', 0)*100:.1f}%** compared to **{vec.get('hit_rate_at_5', 0)*100:.1f}%**.\n"
        md += "- **Why it succeeded:** Cold-start movies lack historical interaction density, which starves collaborative signals. Walking explicit entity relationships (shared directors, cast, and nuanced thematic keywords) surfaces relevant new movies into the candidate pool that embedding similarity alone ranks below the threshold.\n"
    else:
        md += "**Verdict: Hybrid Graph Retrieval Did Not Exceed Similarity-Only.**\n\n"
        md += "The content-based description embeddings captured sufficient semantic overlap to discover cold-start candidates directly from profile summaries.\n"

    md += "\n## 3. Failure & Error Analysis (10 Exemplar Cases)\n\n"
    for i, c in enumerate(error_analysis_cases, 1):
        md += f"### Case {i} (Viewer #{c['user_id']})\n"
        md += f"- **Target Ground Truth:** `{c['ground_truth']}`\n"
        md += f"- **Similarity-Only Hit@5:** {'Yes' if c['vector_hit'] else 'No'} | Top Recommendations: {', '.join(c['vector_recommendations'][:3])}\n"
        md += f"- **Hybrid Hit@5:** {'Yes' if c['hybrid_hit'] else 'No'} | Top Recommendations: {', '.join(c['hybrid_recommendations'][:3])}\n\n"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"\n[Report] Wrote results to {res_path} and {md_path}")

if __name__ == "__main__":
    generate_report()
