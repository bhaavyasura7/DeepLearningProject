# Reference implementations

Two outside repos used as references for CineMind. They are **git submodules**
(links to the original repos at a fixed commit), not copies. Both are MIT-licensed.

Get the code after cloning CineMind:

```bash
git submodule update --init --recursive
```

| Folder | Repo | Pinned commit | Role in our project |
| --- | --- | --- | --- |
| `agentic-recommenders/` | [yxtay/agentic-recommenders](https://github.com/yxtay/agentic-recommenders) | `9c7d028` | Unofficial ARAG implementation (our **base paper**). Outside baseline. |
| `HippoRAG/` | [OSU-NLP-Group/HippoRAG](https://github.com/OSU-NLP-Group/HippoRAG) | `d5c8329` | Official HippoRAG / HippoRAG 2 code. Source of our **Personalized PageRank** retrieval idea. |

Do not edit code inside these folders. Copy ideas into `src/cinemind/` instead.

---

## 1. agentic-recommenders (ARAG, unofficial)

**Paper:** ARAG, arXiv [2506.21931](https://arxiv.org/abs/2506.21931) (Walmart, 2025). Walmart released no official code.

**What it is:** a *simplified* ARAG. The paper's 4 agents are merged into **one**
`pydantic-ai` agent that does everything in one LLM run and calls two tools.
Dataset: MovieLens-1M. Search: LanceDB (vector, full-text or hybrid).

| File | What to look at |
| --- | --- |
| `agentic_rec/agent.py` | **The core.** System prompt with the 3 stages (understand → retrieve → rank) and the two tools `get_item_texts` and `search_items`. |
| `agentic_rec/index.py` | Builds the LanceDB vector + full-text index with sentence-transformers. |
| `agentic_rec/ml_1m.py` | Downloads MovieLens-1M, turns it into Parquet (item text, user history), makes a train/val/test split. |
| `agentic_rec/models.py` | Request/response schemas (`RecommendRequest`, `ItemRecommended`). |
| `agentic_rec/services/recommendation_service.py` | How a request runs through the agent. |

**ARAG paper vs this repo vs CineMind**

| ARAG paper | agentic-recommenders | CineMind (ours) |
| --- | --- | --- |
| User Understanding agent | Stage 1 of the single prompt | `agents/understand.py` |
| NLI agent (does item fit user?) | Not separate | `agents/judge.py` |
| Context Summary agent | Not separate | `agents/summarise.py` |
| Item Ranker agent | Stage 3 of the single prompt | `agents/rank.py` |
| Retrieval: vector | LanceDB vector / FTS / hybrid | ChromaDB vector **+ graph PPR** |
| LLM calls per recommendation | 1 run (with tool calls) | ~9–12 |

So CineMind is **closer to the paper** (4 separate agents) and **adds graph retrieval**.
This repo is useful as a cheaper, 1-agent baseline.

**Run it (needs an LLM key or local Ollama):**

```bash
cd references/agentic-recommenders
uv sync
uv run ml_1m                     # download MovieLens-1M
uv run index                     # build item index
uv run index --parquet_path data/ml-1m/users.parquet --table_name users
export AGENTIC_REC_LLM_MODEL="ollama:qwen3:8b"   # or another pydantic-ai model string
uv run agent                     # recommend for a random user
uv run fastapi run agentic_rec.main:app   # or serve the REST API (POST /recommend)
```

Note: it has **no evaluation script** (no NDCG/Hit numbers). To use it as a baseline,
call its agent on *our* eval viewers and score the output with
`src/cinemind/eval/metrics.py`. It uses MovieLens-1M IDs; our split uses MovieLens-32M,
so movie IDs must be mapped (via title + year, or the TMDB id in `links.csv`).

---

## 2. HippoRAG (official, HippoRAG 2)

**Papers:** HippoRAG, arXiv [2405.14831](https://arxiv.org/abs/2405.14831) (NeurIPS 2024);
HippoRAG 2, arXiv [2502.14802](https://arxiv.org/abs/2502.14802) (2025).

**What it is:** RAG for question answering over documents (not recommendation).
It builds a knowledge graph from text using an LLM, then finds relevant passages by
running **Personalized PageRank** starting from the entities in the question.
We use the same PPR idea, but on a *movie* graph (movie–director–actor–keyword).

| File | What to look at |
| --- | --- |
| `src/hipporag/HippoRAG.py` → `run_ppr()` (~line 2177) | **The PPR step.** Uses igraph `personalized_pagerank`, undirected, edge weights, `damping=0.5` by default. |
| `src/hipporag/HippoRAG.py` → `graph_search_with_fact_entities()` (~line 2008) | How the seed (reset) weights are built from the query before PPR. |
| `src/hipporag/HippoRAG.py` → `index()` (~line 499) | Builds the graph: extract entities/facts with the LLM, add nodes and edges. |
| `src/hipporag/HippoRAG.py` → `retrieve()` (~line 704) | Full retrieval: facts → seeds → PPR → ranked passages. |
| `src/hipporag/StandardRAG.py` | Plain dense-retrieval baseline (no graph). |
| `main.py`, `reproduce/` | Scripts and data to reproduce the paper's numbers. |

**HippoRAG PPR vs CineMind PPR** (`src/cinemind/retrieval/graph.py` → `walk()`)

| | HippoRAG | CineMind |
| --- | --- | --- |
| Graph | Entities + passages, built by an LLM from text | Movies + director/cast/keyword, built from TMDB metadata |
| Seeds | Entities matched to the query, **weighted** by relevance score | Movies from the viewer's history, **equal** weight |
| Damping (chance to follow an edge) | 0.5 (stays closer to seeds) | 0.85 (`config.yaml` → `graph_damping`) |
| Graph size | Whole graph | 2-hop subgraph around seeds |
| Library | igraph (`prpack`) | NetworkX |

Ideas worth trying in CineMind (one at a time, then re-run the eval):
1. Weight seeds by the viewer's rating (e.g. 5★ movie gets more weight than 3★), like HippoRAG weights seeds by relevance.
2. Try `graph_damping: 0.5` as HippoRAG uses.
3. Add seeds from the query text too (match director/actor/keyword names), not only from history.

**Install as a library (not needed for CineMind):**

```bash
pip install hipporag   # Python 3.10, needs an LLM + embedding model; see its README
```
