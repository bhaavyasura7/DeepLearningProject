# CineMind — Project Plan and Research Basis

This file is a handoff for any person or AI agent working on this repo.
It says which research paper the project is built on, what is already done,
what is broken, and what to do next, in order.

---

## 1. The decision (read this first)

**Base paper:** ARAG — *Agentic Retrieval Augmented Generation for Personalized Recommendation*
(Walmart Global Tech, arXiv [2506.21931](https://arxiv.org/abs/2506.21931), June 2025).

**Our extension:** add knowledge-graph retrieval using Personalized PageRank (PPR),
the retrieval idea from HippoRAG / HippoRAG 2
(arXiv [2405.14831](https://arxiv.org/abs/2405.14831), NeurIPS 2024;
arXiv [2502.14802](https://arxiv.org/abs/2502.14802), 2025;
code: [OSU-NLP-Group/HippoRAG](https://github.com/OSU-NLP-Group/HippoRAG)).

**Project claim (one sentence):**
> We implement ARAG's 4-agent recommendation pipeline on MovieLens and extend
> its retrieval step with Personalized PageRank over a director/cast/keyword
> graph, and we test whether this finds relevant *cold-start* movies
> (new movies with few or no ratings) that vector similarity alone misses.

### Why this paper and not the others

| Reason | Detail |
| --- | --- |
| Recent | Published 2025, fits the "2024–2025 papers only" requirement. |
| No official code | Walmart did not release code, so our implementation is a real contribution, not a copy. |
| No GPU training needed | Runs on LLM calls only (local Ollama). Alternatives such as K-RagRec, LlamaRec-LKG-RAG and Rank-GRPO need fine-tuning on large GPUs. |
| Already mostly built | This repo already has the 4 agents, vector + graph retrieval, and metrics code. |
| Clear, testable extension | ARAG uses only vector retrieval; adding graph retrieval is one clean, measurable change. |

### Do NOT switch papers

Do not restart the project on a different paper. The papers below are for
**related work and comparison only**.

---

## 2. Mapping: ARAG paper → this repo

| ARAG component (paper) | File in this repo | Notes |
| --- | --- | --- |
| User Understanding Agent | `src/cinemind/agents/understand.py` | Builds viewer profile from history + query. |
| NLI Agent (does item match user?) | `src/cinemind/agents/judge.py` | Batched, 10 candidates per call. |
| Context Summary Agent | `src/cinemind/agents/summarise.py` | |
| Item Ranker Agent | `src/cinemind/agents/rank.py` | |
| (not in paper) Output guards | `src/cinemind/agents/guards.py` | Our addition: candidate-set check, extractive quotes. |
| Retrieval: vector (what ARAG uses) | `src/cinemind/retrieval/vector.py`, `embed.py` | ChromaDB + `nomic-embed-text`. |
| Retrieval: graph PPR (**our extension**) | `src/cinemind/retrieval/graph.py` | NetworkX, damping 0.85, 2 hops. |
| Retrieval: hybrid merge (**our extension**) | `src/cinemind/retrieval/hybrid.py` | Interleave + de-duplicate, cap 50. |
| Orchestrator | `src/cinemind/pipeline.py` | |
| Metrics (NDCG, Hit, Recall) | `src/cinemind/eval/metrics.py` | Same metrics as the paper (NDCG@5, Hit@5). |
| Eval split + runner + report | `src/cinemind/eval/split.py`, `run.py`, `report.py` | |
| Settings | `config.yaml` | |

---

## 3. Current problem: the saved results are not real

`demo/results/results.md` shows **0.0000 for every metric in every configuration**,
and almost every viewer gets the same recommendations
("Branded, Altered States, Parallels"). These numbers must not be reported.

Known cause:

- `make eval` runs `python -m src.cinemind.eval.run` **without `--live`**.
  In `src/cinemind/eval/run.py`, `LLMClient(stub=not use_live)` therefore uses
  the **stub (fake) LLM**. The ~0.04 s per recommendation confirms no real model ran.

Also check:

- `src/cinemind/retrieval/embed.py` silently falls back to
  `deterministic_fallback_embedding` (a word-hash vector, not a real embedding)
  when Ollama is not reachable. If the vector index was built that way, vector
  retrieval is meaningless. Rebuild the index with Ollama running.
- `Recall@50 = 0` means the ground-truth movies are not even among the
  50 candidates, before any LLM ranking. Confirm the ground-truth cold-start
  movies actually exist in the catalog / vector index / graph. If they are
  missing, no configuration can ever score above 0.

---

## 4. Next steps (do them in this order)

1. **Fix the evaluation so it uses real models.**
   - Start Ollama, pull `qwen3:8b` and `nomic-embed-text`.
   - Rebuild indexes: `make index` (confirm no fallback embeddings are used).
   - Delete `demo/results/eval_checkpoint.jsonl` (it caches the stub runs).
   - Run with `--live`: `python -m src.cinemind.eval.run --live --viewers 50`
     (start small; go to 200 once it works).
   - Make `make eval` pass `--live`, or make the report say clearly when stub mode was used.

2. **Sanity-check retrieval before the LLM.** For a few viewers, check that
   ground-truth movies appear in the candidate list (`Recall@50 > 0`).
   If not, fix the catalog/index, not the agents.

3. **Run the main comparison** (same viewers, same split, same LLM):

   | # | Configuration | What it represents |
   | --- | --- | --- |
   | 1 | Plain RAG: vector retrieval, single LLM ranking call | Standard RAG baseline (as in the ARAG paper) |
   | 2 | ARAG: 4 agents + vector retrieval (`retrieval="vector"`) | Paper re-implementation |
   | 3 | CineMind: 4 agents + hybrid retrieval (`retrieval="hybrid"`) | **Our method** |
   | 4 | 4 agents + graph-only retrieval (`retrieval="graph"`) | Ablation |

   Configuration 1 does not exist yet; add it as a simple baseline.

4. **Report** NDCG@5, Hit@5 (paper's metrics), plus NDCG@10, Hit@10, Recall@50,
   LLM calls per recommendation and seconds per recommendation.
   Report the **cold-start subset separately**; that is where the graph should help.

5. **Write up honestly.** If hybrid does not beat vector-only, say so and show
   failure cases. A negative result with a correct setup is acceptable;
   numbers from the stub LLM are not.

6. **Optional extras, only after 1–5 are done:**
   - Run [yxtay/agentic-recommenders](https://github.com/yxtay/agentic-recommenders)
     (unofficial single-agent ARAG, MovieLens-1M, MIT license) as an outside baseline.
   - Use [Agent4Rec](https://github.com/LehengTHU/Agent4Rec) simulated users for extra evaluation.

---

## 5. Related work (cite, do not implement)

All have public code unless marked.

| Paper | Year / venue | Code | Relation to us |
| --- | --- | --- | --- |
| ARAG | 2025, arXiv 2506.21931 | No official code; unofficial: [yxtay/agentic-recommenders](https://github.com/yxtay/agentic-recommenders) | **Base paper** |
| HippoRAG 2 / HippoRAG | 2025 / NeurIPS 2024 | [OSU-NLP-Group/HippoRAG](https://github.com/OSU-NLP-Group/HippoRAG) | **Source of the PPR retrieval idea** |
| CRAG — Collaborative Retrieval for LLM-based CRS | WWW 2025 | [yaochenzhu/CRAG](https://github.com/yaochenzhu/CRAG) | LLM + collaborative-filtering retrieval |
| MACRec — Multi-Agent Collaboration for Recommendation | SIGIR 2024 | [wzf2000/MACRec](https://github.com/wzf2000/MACRec) | Another multi-agent recommender |
| Agent4Rec — On Generative Agents in Recommendation | SIGIR 2024 | [LehengTHU/Agent4Rec](https://github.com/LehengTHU/Agent4Rec) | LLM user simulator on MovieLens-1M |
| Rank-GRPO / ConvRec-R1 | arXiv 2510.20150, ICLR 2026 | [yaochenzhu/Rank-GRPO](https://github.com/yaochenzhu/Rank-GRPO) | RL training of LLM recommenders (needs GPUs) |
| K-RagRec — KG RAG for LLM-based Recommendation | ACL 2025 | Not found | KG retrieval for LLM recs, MovieLens-1M/20M |
| LlamaRec-LKG-RAG | arXiv 2506.07449, 2025 | Paper says code exists; link not verified | Trainable KG-RAG ranker on ML-100K |

---

## 6. Reference code in this repo

Both reference implementations are included as git submodules under `references/`
(run `git submodule update --init --recursive` to download them).
See `references/README.md` for which files matter and how they compare to CineMind.

- `references/agentic-recommenders/` — unofficial ARAG (base paper).
- `references/HippoRAG/` — official HippoRAG 2 (Personalized PageRank idea).

## 7. Rules for anyone continuing this work

- Keep ARAG as the base paper; do not switch to another paper.
- Never report metrics produced with the stub LLM or fallback embeddings.
- Use the same eval split (`demo/results/eval_viewers.json`, seed 42) for every configuration.
- Change one thing at a time and re-run the comparison.
- Run `make test` before committing.
