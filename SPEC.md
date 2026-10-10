# ARAG + GRU — Project Specification (v3, final)

Self-contained build spec. A developer or coding agent should be able to build the whole project from this file alone. It consolidates every decision made so far; where it differs from earlier drafts, this file wins.

---

## 0. Instructions for the agent building this

1. Read this whole file before writing code.
2. Build the **entire system in one pass** (Phase A research core + Phase B product demo). There is no separate "debug run" phase.
3. **Never fabricate results.** Every number in `results/` must come from a real run on real data with the real LLM. If the dataset cannot be downloaded or `OPENAI_API_KEY` is missing, build and test the code, then stop and say exactly what is missing. Do not commit stub or fake metrics, traces or demo data.
4. Unit and integration tests use small hand-made fixtures and a **fake LLM client**. Those exist only so tests run without network/keys; their outputs must never be written to `results/` or `artifacts/`.
5. Work on the branch you were given; commit in logical steps with clear messages.
6. When done, report: what was built, test results, the actual metrics table (if the real run happened), actual LLM cost, and anything not done.

### Environment prerequisites (cloud session)
- Network allowlist must include: `huggingface.co`, `cdn-lfs.huggingface.co`, `cdn-lfs-us-1.huggingface.co`, `cas-bridge.xethub.hf.co` (dataset + sentence-transformer model), plus package managers (PyPI, npm). `api.openai.com` must be reachable.
- Environment variable / secret: `OPENAI_API_KEY`. Read it from the environment only; never print, log or commit it. Never put it in `.env.example` with a value.

---

## 1. What the project is

An ARAG-style agentic recommender (Maragheh et al., 2025, arXiv:2506.21931) on Amazon Reviews 2023 (Video Games), extended with **one deep-learning contribution: a trained PyTorch GRU sequential user model fused into the final ranking**. Plus a web demo with a personalised feed, product search, feedback and persistent memory.

- **Primary question:** on identical frozen candidate lists, does fusing a GRU score into ARAG's LLM ranking improve Hit@5 / NDCG@5 over ARAG alone and over the GRU alone?
- **H1:** ARAG+GRU > ARAG (α = 1). **H2:** ARAG+GRU > GRU alone (α = 0).
- **Secondary:** check the paper's ordering (LLM-Recency, LLM-Vanilla-RAG < ARAG) and its two ablations on our data; report cost/latency.
- This is **ARAG-inspired, not an exact reproduction**: the paper does not publish prompts, NLI threshold, candidate-list size or code, and used gpt-3.5-turbo on an older Amazon dataset. Never compare our numbers directly with the paper's Table 1.
- Negative or mixed results are valid outcomes and must be reported as measured.

---

## 2. Fixed decisions

| Topic | Decision |
|---|---|
| Dataset | Amazon Reviews 2023 (McAuley Lab), category **Video_Games**. Fallback **All_Beauty** only if Video_Games 5-core is unusable (record why). |
| Split | The dataset's official **rating-only 5-core, leave-last-out** benchmark split (last item = test, second-to-last = validation, rest = train). |
| Item text | Product metadata only (title, main_category, categories, features, description), truncated to ~120 words. No review text. |
| LLM | OpenAI **gpt-4o-mini**, temperature 0, structured JSON output (JSON schema), pinned model string in config. |
| Embeddings | sentence-transformers **all-MiniLM-L6-v2**, normalised, FAISS `IndexFlatIP`. |
| Deep learning | PyTorch **GRU4Rec-style** model, trained on train sequences only. |
| Evaluation users | **100 test users** and **100 validation users** for every LLM-based system (fixed seed). Non-LLM systems (Random, Popularity, GRU) are additionally reported on **all** test users. |
| Candidate lists | Per user: **target + 19 negatives = 20 items**, frozen and shared by every system. |
| Primary metrics | Hit@5, NDCG@5; also Hit@10, NDCG@10, MRR; paired-bootstrap 95% CIs. |
| Orchestration | Plain async Python for the agent pipeline (LangGraph not required). |
| API / storage / UI | FastAPI + Pydantic, **SQLite**, **React + Vite** frontend. |
| Experiment log | JSON run records (MLflow not used). |
| Python | 3.11+ (3.13 fine), dependencies pinned (`requirements.txt` with versions or `uv.lock`). |
| Budget | ≈ **$1** of gpt-4o-mini for the full evaluation (§10). Hard stop if spend estimate exceeds $5. |

---

## 3. Repository layout

```
README.md  SPEC.md  Makefile  requirements.txt  .env.example  .gitignore
configs/
  config.yaml              # all paths, seeds, sizes, model names, θ grid, α grid
  prompts/                 # uua.txt nli.txt csa.txt ira.txt recency.txt vanilla_rag.txt
data/                      # git-ignored: raw/ processed/
artifacts/                 # git-ignored: lists/ gru/ faiss/ llm_cache/ predictions/ app.db
results/                   # tracked: metrics.json, tables.md, alpha_curve.png, cost.json, run_record.json, report.md
src/arag/
  config.py
  dataprep/  download.py  load.py  items.py  lists.py  manifest.py
  models/    gru.py  train_gru.py  score.py
  retrieval/ embed.py  index.py
  llm/       client.py  cache.py  fake.py  schemas.py
  agents/    context.py  uua.py  nli.py  csa.py  ira.py  arag.py  baselines.py
  ranking/   parser.py  fusion.py  simple.py      # random, popularity
  eval/      metrics.py  bootstrap.py  run.py  report.py
  memory/    db.py  repo.py                        # SQLite
  api/       app.py  routes.py  schemas.py  services.py
frontend/                  # React + Vite
tests/
```

**.gitignore rule:** anchor ignores to the repo root (`/data/`, `/artifacts/`, `/.venv/`, `node_modules/`, `.env`). A bare `data/` rule silently ignores *any* folder named `data`, including source packages — this broke the previous version of this repo. Name the code package `dataprep/`, not `data/`. Add a test that every module under `src/` is tracked by git.

---

## 4. Data pipeline (`src/arag/dataprep`)

1. **Download** from Hugging Face dataset `McAuley-Lab/Amazon-Reviews-2023`:
   - the rating-only 5-core leave-last-out benchmark files for Video_Games (train / valid / test), and
   - the item metadata for Video_Games (`raw_meta_Video_Games`).
   Verify exact file names/configs against the dataset card before coding the loader; do not guess silently. Save under `data/raw/`.
2. **Manifest** (`data/manifest.json`, tracked copy in `results/`): dataset id, category, files, download date, row counts, SHA-256 per file.
3. **Load** into Parquet tables:
   - `interactions(user_id, item_id, timestamp, rating, split)`; item_id = `parent_asin`.
   - `items(item_id, title, text, main_category, price)`.
   Log row counts at every step; drop rows with missing ids/timestamps and log how many (no silent row loss). Items without metadata/title: keep them in interactions but mark `has_text=false`; log the count.
4. **Sequences** per user, sorted by (timestamp, item_id):
   - train sequence = train-split interactions;
   - validation target = the valid-split item; its history = train sequence;
   - test target = the test-split item; its history = train sequence + validation item.
   Assert for every user: max(train ts) ≤ valid ts ≤ test ts, and targets are not in their own history.
5. **Context for prompts** (`agents/context.py`), built only from history strictly before the target:
   - **Session context C_st** = last 5 history items.
   - **Long-term context C_lt** = up to 50 items before those 5.
   - Each item rendered as `title | main_category | rating | YYYY-MM-DD`.
6. **User samples** (seed 42): 100 validation users and 100 test users, drawn from users whose target item has text. Save ids to `artifacts/lists/users.json`.
7. **Frozen candidate lists** (`dataprep/lists.py`), for every validation and test user (all users, not just the 100, so non-LLM systems can use them):
   - 19 negatives sampled uniformly (seed 42) from catalogue items with text that the user **never** interacted with in any split;
   - add the target, shuffle with a seeded RNG, store the order;
   - save `artifacts/lists/{valid,test}_lists.parquet` + SHA-256; never regenerate after evaluation starts.
   - Random-ranking reference: Hit@5 = 0.25.

---

## 5. Systems compared

All systems rank the **same frozen 20-item list per user**.

| System | Definition | LLM calls/user |
|---|---|---|
| Random | Seeded random permutation | 0 |
| Popularity | Order by train interaction count | 0 |
| GRU (α = 0) | Order by GRU score | 0 |
| LLM-Recency (paper baseline) | Last 10 history items + 20 candidates in one ranking prompt | 1 |
| LLM-Vanilla-RAG (paper baseline) | The 10 history items most similar (MiniLM cosine) to the mean candidate embedding + 20 candidates in one ranking prompt | 1 |
| ARAG (α = 1) | UUA ∥ NLI → CSA → IRA (§6) | 7 |
| ARAG w/o NLI (paper ablation) | CSA summarises all 20 candidates; then IRA | 2 (UUA reused) |
| ARAG w/o NLI & CSA (paper ablation) | IRA gets S_user + raw candidate list | 1 (UUA reused) |
| **ARAG + GRU (proposed)** | Late fusion of ARAG ranking and GRU score (§7.3) | 0 extra (reuses ARAG) |

---

## 6. ARAG agents (`src/arag/agents`)

All agents: prompt files in `configs/prompts/`, output validated by Pydantic schemas, candidates referenced by their `item_id`, candidates shown in the frozen list order.

**6.1 User Understanding Agent (UUA)** — input C_lt, C_st. Output `{long_term_interests: [str], current_intent: str, avoid: [str], summary: str (≤120 words)}`.

**6.2 NLI Agent** — input: raw user context (C_lt + C_st, *not* the UUA output, so it runs in parallel with UUA as in the paper) and 5 candidates per call (4 calls). Output per candidate `{item_id, label: "support"|"neutral"|"contradict", score: int 0–10, rationale: str}`. Accepted set I⁺ = score ≥ θ, θ ∈ {4,5,6,7} tuned on validation NDCG@5 (default 6). Missing/unknown ids: re-ask once for the missing items only; if still missing, score 5 + increment `nli_missing`.

**6.3 Context Summary Agent (CSA)** — input S_user, item text and NLI scores of I⁺ ordered by score. Output `{summary: str (≤200 words)}`. If I⁺ is empty, use the top 3 by NLI score and set `csa_empty_fallback = true`.

**6.4 Item Ranker Agent (IRA)** — input S_user, S_ctx, all 20 candidates (title + text). Prompt follows the paper: consider the user's previous behaviour, consider the relevant part of history, examine the candidates, rank in descending order of likelihood of interaction. Output `{ranking: [20 item_ids], reasons: {item_id: one-line reason} for the top 5}`.

**6.5 Ranking parser** (`ranking/parser.py`, used by IRA and the two LLM baselines) — drop unknown ids, drop duplicates (keep first), append missing ids at the end (by NLI score if available, else list order). Count each repair type; report repair rate per system.

**6.6 Execution per user**
```
parallel:  S_user = UUA(C_lt, C_st)                 # 1 call
           nli    = NLI(u, candidates)              # 4 calls
then:      S_ctx  = CSA(S_user, accepted(nli, θ))   # 1 call
then:      π      = IRA(S_user, S_ctx, candidates)  # 1 call
```
Run up to 8 users concurrently (configurable) to respect rate limits.

**6.7 LLM client** (`llm/client.py`)
- OpenAI SDK, model from config (`gpt-4o-mini`), temperature 0, JSON-schema response format, timeout 60 s, exponential backoff on 429/5xx.
- On invalid JSON/schema: one retry with the validation error appended; then the documented fallback for that agent, counted in the run record. Never silent.
- **Disk cache** `artifacts/llm_cache/` keyed by SHA-256 of (model, prompt, schema). A cache hit makes no API call. Re-running the evaluation must make **zero** new calls.
- Log per call: agent, tokens in/out, latency, cache hit, error. Running cost estimate printed during evaluation; abort if it exceeds `budget.max_usd` (default 5).
- `llm/fake.py`: deterministic fake client for tests only.

---

## 7. GRU model and fusion (`src/arag/models`, `src/arag/ranking/fusion.py`)

**7.1 Model** — item embedding 64-d → 1-layer GRU (hidden 128) → dropout 0.2 → user vector h_u = last valid hidden state. Item vocab = items in train interactions; index 0 = padding, 1 = OOV. Input embeddings tied to output embeddings (project h_u to 64-d if hidden ≠ 64).

**7.2 Training** — sequences = last 50 train items, left-padded, masked (`pack_padded_sequence`). Objective: next-item prediction, full-softmax cross-entropy over the vocab, trained on every prefix. Adam, lr 1e-3, batch 256, up to 30 epochs, early stopping (patience 3) on **validation NDCG@5 over the frozen validation lists** (all validation users). Small grid on validation only: hidden {64, 128}, dropout {0.2, 0.5}. Train **3 seeds** (0, 1, 2) with the best config; report mean ± std. Save `artifacts/gru/{seed}/` = checkpoint + item map + config together. CPU must be enough (minutes).

**7.3 Scoring and fusion** — GRU(u, i) = h_u · e_i (OOV → OOV embedding; report OOV rate among candidates/targets).
```
s_llm(i) = 1 - (rank_IRA(i) - 1) / 19
s_gru(i) = 1 - (rank_GRU(i) - 1) / 19
final(i) = α·s_llm(i) + (1-α)·s_gru(i),  α ∈ {0.0, 0.1, …, 1.0}
ties: higher NLI score, then item_id
```
α chosen on validation NDCG@5 (100 validation users, seed-0 GRU), then applied to test. Report the full α curve for validation and test. α = 1 must reproduce IRA order exactly; α = 0 must reproduce GRU order exactly.

---

## 8. Evaluation (`src/arag/eval`)

- **Hit@K** = 1 if target rank ≤ K. **NDCG@K** = 1/log₂(rank+1) if rank ≤ K else 0. **MRR** = 1/rank.
- **Paired bootstrap**: 10,000 resamples of users; 95% CI of the per-user metric difference for every system vs ARAG and vs GRU. CI containing 0 ⇒ "no significant difference".
- **Retrieval Recall@K** (no LLM, all test users): embed C_st+C_lt titles, FAISS search over all items with text, excluding history; report Recall@{20, 50, 100} of the target. This characterises the retrieval used by the demo; it is not part of the ranking comparison.
- **Cost**: calls, tokens in/out, USD (using prices in config), seconds per user, per system; parser repair rate and fallback counts per system.
- Save per-user predictions `artifacts/predictions/{system}.parquet` (`user_id, ranked_ids, target, rank`) and copy a tracked CSV to `results/predictions/`.
- `results/report.md` is generated from saved artifacts only: data stats, protocol, main table (100 test users, all systems, with CIs), non-LLM table on all test users, α curve, ablations, cost table, limitations. Text conclusions must be computed from the numbers (no pre-written verdicts).
- Limitations to state: leave-last-out means other users' later interactions can be in GRU training; 100 users ⇒ wide CIs (~±10 points on Hit@5); uniform negatives are easier than real retrieval; not an exact paper reproduction.

---

## 9. Phase B — product demo

**9.1 Memory (SQLite, `artifacts/app.db`)**
```
users(user_id PK, created_at, is_synthetic)
items(item_id PK, title, text, main_category, price)
interactions(event_id PK, user_id, item_id, ts, event_type, rating, source)   -- source: dataset|app
profiles(user_id PK, profile_json, provenance_json, version, updated_at)      -- UUA output + event ids used
sessions(session_id PK, user_id, created_at, updated_at)
session_events(event_id PK, session_id, user_id, item_id, event_type, ts, payload_json)
rec_runs(run_id PK, user_id, session_id, kind, request_json, config_json, created_at)
rec_items(run_id, item_id, rank, score, reason_json)
```
Indexes on interactions(user_id, ts), session_events(session_id, ts). Event types: `view, click, like, dismiss, save` (distinct; a click is not a purchase). Seed the DB with **8 real test users** (their dataset history up to the test target) and all items with text. Synthetic users, if any, must have `is_synthetic=1` and never enter metrics.

**9.2 Flows**
- **Search:** parse query (LLM call with schema `{keywords, max_price, exclude_terms}`; explicit constraints override inferred preferences) → filter items by hard constraints → FAISS top 50 on query embedding → drop dismissed/already-interacted → top 20 → ARAG + GRU fusion (α from evaluation) → top 5 with reasons. Each reason shows an evidence snippet that is an exact substring of the item text, selected in code (never generated).
- **Feed:** FAISS top-K on the user-context embedding ∪ GRU top-N over the catalogue → de-duplicate, drop interacted/dismissed → 20 candidates → ARAG + GRU → paginated (page_size 10; rank once per page request, cache the run).
- **Feedback:** stored immediately; the next request's session context (C_st) includes app events. `dismiss` excludes the item for that user. No online GRU retraining; the GRU vector is recomputed from the current sequence at request time.
- **Profile:** UUA output stored with provenance; regenerated when ≥ 5 new events since last version; viewable and deletable.
- **Replay:** every demo request is a `rec_run`; with the LLM cache, a run can be replayed with zero API calls. `REPLAY_ONLY=1` makes the API refuse uncached LLM calls (offline demo).

**9.3 API (FastAPI)**
| Method / path | Purpose |
|---|---|
| GET `/health` | DB, FAISS index, GRU checkpoint, LLM key present (boolean only) |
| GET `/users` | Demo users list |
| POST `/sessions` | Create/resume session `{user_id, session_id?}` |
| GET `/feed?user_id&session_id&page&page_size` | Personalised feed |
| POST `/search` | `{user_id, session_id, query, filters?, limit?}` |
| POST `/feedback` | `{user_id, session_id, item_id, event_type}` |
| GET `/users/{id}/profile` · DELETE `/users/{id}/profile` | Inspect / delete profile memory |
| GET `/runs/{run_id}` | Trace: stages, candidates, NLI scores, S_user, S_ctx, final ranking, fusion scores |
| POST `/runs/{run_id}/replay` | Replay from cache |
| GET `/results` | Serves `results/metrics.json` |

Pydantic request/response models, consistent error format, 400/404/503 as appropriate. Bind to 127.0.0.1. A user can only access their own profile/session (check user_id matches session).

**9.4 Frontend (React + Vite, `frontend/`)**
- User picker (demo users), Feed tab (cards with title, category, price, reason, evidence snippet, like/dismiss/save buttons), Search tab (query box + optional max price), Profile panel (current profile + delete), Run trace drawer (agent outputs per stage), Results tab (metrics table + α curve from `/results`).
- Clearly label fallbacks/repairs in the trace. Works at phone width. No build step needed to run the API; `npm run build` output served by FastAPI at `/`.

---

## 10. Budget (gpt-4o-mini, $0.15 / 1M input, $0.60 / 1M output — verify current prices)

| Part | Users | ≈ Cost |
|---|---|---|
| Test: ARAG + both LLM baselines + both ablations (~12 calls, ~26k in / ~3.4k out tokens per user) | 100 | $0.60 |
| Validation: ARAG (7 calls) | 100 | $0.35 |
| θ tuning (CSA + IRA re-run for 4 θ values) | 100 | ~$0.10 |
| **Total evaluation** | | **≈ $1.05** |
| Demo usage | — | cents |

Expanding test users to 300 later costs ≈ +$1.20 and reuses the cache for the first 100.

---

## 11. Tests (`tests/`, pytest, no network, fake LLM)

| Area | Test |
|---|---|
| Split | train ts ≤ valid ts ≤ test ts; targets not in own history (on a fixture) |
| Leakage | prompt builder for a target never includes the target or anything at/after its time |
| Lists | 20 unique items, target exactly once, no item the user ever interacted with, byte-identical on regeneration |
| Metrics | hand-computed Hit@K, NDCG@K, MRR; bootstrap on a known case |
| Parser | malformed / duplicate / missing / unknown ids → valid 20-permutation with correct repair counts |
| GRU | padding masked (padded vs unpadded same h_u); save → load reproduces scores; trains and beats random on a toy sequential fixture |
| Fusion | α=1 ≡ IRA order; α=0 ≡ GRU order |
| Cache | second run makes zero client calls and identical outputs |
| Agents | NLI missing-id re-ask then neutral fill; CSA empty fallback; schema retry then fallback counted |
| API | health, sessions, feed, search, feedback persists and changes next feed, dismiss excludes item, profile delete, cross-user access rejected, replay with REPLAY_ONLY |
| Repo | every module under `src/` is tracked by git |

---

## 12. Commands (`Makefile`)

```
make setup      # venv + pip install -r requirements.txt + npm ci in frontend/
make data       # download + manifest + parquet tables
make lists      # sequences, user samples, frozen candidate lists
make index      # MiniLM embeddings + FAISS
make gru        # train GRU (grid + 3 seeds)
make eval       # all systems on validation (θ, α tuning) then test; resumable via cache
make report     # results/*.md|json|png from artifacts
make test       # pytest
make app        # build frontend, seed DB, run API on 127.0.0.1:8000
make all        # data lists index gru eval report
```
`make eval` prints the running cost and stops above `budget.max_usd`. Everything is resumable: re-running skips finished work.

---

## 13. Definition of done

- `make all` on a fresh clone (with network allowlist + `OPENAI_API_KEY`) produces `results/report.md`, `metrics.json`, tables, α curve, cost table, run record (git commit, config, seeds, model id, dataset manifest).
- All systems in §5 evaluated on the same frozen lists for 100 test users (non-LLM also on all test users), with paired-bootstrap CIs.
- `make test` passes without network or API key.
- `make app` runs the demo: pick a real test user, see a feed, search, like/dismiss, see the feed change, inspect the run trace and profile, view results.
- README explains setup, environment prerequisites, commands, cost, and how to read the results.
- No fabricated or stub-generated numbers anywhere in the repo.

---

## 14. Decision history (why things are this way)

- **Frozen 20-item lists** instead of FAISS top-K for evaluation: otherwise a missed retrieval scores 0 for every method and the comparison measures retrieval, not ranking.
- **Late fusion** for the GRU: the ARAG ranker is an LLM producing a permutation and cannot take a vector; fusion also costs no extra LLM calls and makes the GRU contribution exactly ablatable.
- **GRU kept**: it is the only trained deep-learning component; without it nothing is trained. It costs minutes of CPU and $0.
- **LLM cost depends only on the number of evaluated users**, not dataset size; 100 test users ≈ $1 with gpt-4o-mini. Dataset size only affects download and GRU training time.
- **100 test users**: enough to detect gains of the paper's size (~10–15 points, paired comparisons); small differences will show as non-significant and must be reported that way.
- **Dropped** the "without session" / "without long-term" ablations to keep cost down.
- **Session context = last 5 items**: Amazon reviews have no real sessions; app feedback events (click, like, dismiss) exist only in the demo and are not evaluated offline.
- **Previous CineMind implementation was removed**: missing data package (bare `data/` gitignore rule), synthetic evaluation split, stub-generated results and traces.
