# CineMind — Spec, Plan, Tasks

Generated in the `spec-writer` format (Spec → Plan → Tasks → Assumptions). Source: CineMind project document (ARAG reproduction + graph-retrieval extension for movies).
Compatible with GitHub Spec Kit / OpenSpec: drop into `.specify/` or `openspec/changes/cinemind/`.

---

# SECTION 1: SPEC

## One-line purpose

A person can get five explained movie recommendations, either by typing a request or with no input at all (from viewing history), watch each of four reasoning stages do its work, and see evidence that adding graph-based candidate discovery finds new movies that similarity-only discovery misses.

## Users and use cases

- As a **demo viewer** (faculty, recruiter, friend, with no technical background), I want to click a ready-made scenario and see recommendations appear with reasons so that I understand what the system does in under three minutes.
- As a **demo viewer**, I want to see the same request answered with and without graph discovery side by side so that I can see the improvement myself.
- As a **demo viewer** on a machine where the language model is not running, I want a replay of recorded runs so that the demo never fails in front of an audience.
- As an **evaluator**, I want to run a reproducible cold-start experiment with three retrieval configurations so that I can report whether the improvement is real.
- As an **operator**, I want to go from a fresh clone to a working demo with documented commands so that anyone can reproduce it.

## Requirements

1. **Query mode.** Given free text (e.g. "fun sci-fi like Inception but shorter"), return a ranked list of five movies.
2. **Feed mode.** Given only a viewer's rating history (no text), return a ranked list of five movies.
3. **Four ordered stages.** (a) Understanding: produce a structured preference profile from history and/or query. (b) Judging: for every candidate, decide match / no match with a fit score and a one-line reason. (c) Summarising: compress all judgements into one brief. (d) Ranking: output the final ranked list with a reason per item.
4. **Two discovery sources.** Candidates come from (i) similarity of movie descriptions to the profile and (ii) walking relationships between movies, cast, crew, and genres starting from movies the viewer liked. The system supports three switchable configurations: similarity-only, graph-only, hybrid (union, de-duplicated, capped at 50).
5. **No invented movies.** Every recommended movie exists in the catalog and was in the candidate set for that run.
6. **Explainability.** Every recommendation shows: a reason, how it was discovered (e.g. "same director as *Movie X*" or "similar description"), and a verbatim quote from that movie's own description as evidence.
7. **Live progress.** While running, the interface shows each stage starting and finishing, with intermediate outputs viewable.
8. **Comparison view.** For a chosen scenario, show similarity-only results and hybrid results side by side, highlighting movies that appear only in hybrid.
9. **Preset scenarios.** At least 6 one-click scenarios: ≥2 query-mode, ≥2 feed-mode, ≥2 featuring a brand-new movie that has no ratings in the training period.
10. **Replay mode.** Every preset scenario has a recorded run that renders fully without the language model or network.
11. **Evaluation.** A cold-start experiment with a time-based split, HitRate@5/10 and NDCG@5/10, three configurations, results saved as files and viewable in the interface, plus cost per recommendation (model calls, seconds).
12. **Failure transparency.** When a stage fails or falls back, the interface says so; it never silently shows degraded results as normal.
13. **Reproducible setup.** Fresh clone → working demo using only documented commands; after the one-time data build the demo needs no internet.

## Edge cases

- Empty query **and** empty history → request rejected with a clear message; nothing is run.
- Fewer than 5 candidates judged "match" → remaining slots filled by highest fit score among "no match", each labelled as a weak match.
- A stage returns malformed output → retried once; if still malformed, a deterministic fallback is used and the interface shows a "fallback used" badge.
- The ranking stage names a movie outside the candidate set → that entry is dropped and replaced by the next best candidate.
- A movie lacks a description → excluded from the catalog at build time (never reaches discovery).
- Two movies share a title (remakes) → identified by id and release year everywhere, including displays.
- The language model is unavailable at request time → live mode returns a clear error and offers replay for preset scenarios.
- Evaluation interrupted midway → rerun resumes from the last completed viewer without recomputing finished ones.
- A viewer's history contains movies not in the catalog → those entries are ignored and counted in the trace.
- The rating data's latest timestamp is earlier than the planned test period → build step fails loudly with the actual max date.

## Acceptance criteria

```
Given the demo is running with the model available
When a viewer submits the query "fun sci-fi like Inception but shorter"
Then exactly 5 movies are returned, each with reason, discovery path, and evidence quote

Given a preset feed-mode scenario for a viewer with history
When the viewer clicks it and no text is entered
Then 5 movies are returned and none of them is in that viewer's history

Given any completed run
When the returned movie ids are compared to that run's candidate ids
Then every returned id is in the candidate set

Given any recommendation with an evidence quote
When the quote is searched in that movie's catalog description
Then it is found as an exact substring

Given the model server is stopped
When the viewer opens a preset scenario in replay mode
Then results render in under 1 second with a "replay" badge and no error

Given the model server is stopped
When the viewer submits a live request
Then an error message states the model is unavailable and offers replay; no partial results are shown as final

Given the comparison view for a cold-start scenario
When it renders
Then it shows two result lists and marks every movie present in hybrid but absent from similarity-only, each with its discovery path

Given a stage output that is malformed twice in a row
When the pipeline continues
Then the run completes using the deterministic fallback and the stage shows a "fallback used" badge

Given the empty query and an empty history
When the request is submitted
Then it is rejected with a message and no stage runs

Given a fresh clone on a supported machine
When the operator follows the README setup commands in order
Then the demo starts and at least the replay scenarios work

Given the evaluation is interrupted after 50 of 200 viewers
When it is started again
Then it processes only the remaining 150 viewers and the final tables are identical to an uninterrupted run (same seed)

Given completed evaluation
When results are opened in the interface and in the results file
Then both show HitRate@5, HitRate@10, NDCG@5, NDCG@10 for all three configurations, plus cost per recommendation

Given the same seed and inputs
When the evaluation split is built twice
Then both splits are byte-identical
```

---

# SECTION 2: PLAN

## Stack and architecture

- **Machine target:** Apple Silicon Mac, 16 GB unified memory. Budget: model ≤ ~9 GB resident, leaving room for macOS, the vector index, and a browser.
- **Language / packaging:** Python 3.11, virtualenv, `requirements.txt`, `Makefile` for all commands.
- **Model server:** Ollama (current release; uses Apple's MLX path automatically on Apple Silicon). Structured JSON output via Ollama's `format` parameter with a JSON schema (not tool calling).
- **Model choice:** primary `gemma4:12b` (about 7–8 GB at Q4, native 256K context). Fallback `qwen3.5:9b` (about 6–7 GB). Rejected: `gpt-oss:20b` (≈14 GB weights — too tight on 16 GB), 27B+ and 30B models (≥17 GB). A bake-off task (Task 2) confirms the choice on the actual machine; the winner is written to config. Run with `OLLAMA_MAX_LOADED_MODELS=1` so models never co-reside.
- **Embeddings:** `nomic-embed-text` through Ollama. **Vector store:** Chroma, persistent on disk. **Graph:** NetworkX in memory, pickled to disk.
- **Orchestration:** plain Python async pipeline (the flow is linear; no graph-orchestration framework).
- **Server:** FastAPI on `127.0.0.1`, Server-Sent Events for stage streaming. **Frontend:** one static HTML + vanilla JS page served by the same server; no build step.
- **Data:** MovieLens 32M (ratings, links) and TMDB API (descriptions, cast, crew, genres, keywords, poster path). Raw data is downloaded by `make data`, never committed.

## Repository layout

```
cinemind/
  Makefile  README.md  requirements.txt  .env.example  config.yaml
  data/            # gitignored: raw/, processed/ (catalog.jsonl, graph.pkl, chroma/)
  demo/            # committed: scenarios.json, traces/*.json (recorded runs), results/ (eval outputs)
  src/cinemind/
    config.py  llm.py  schemas.py
    data/{movielens.py,tmdb.py,build_catalog.py}
    retrieval/{embed.py,vector.py,graph.py,hybrid.py}
    agents/{understand.py,judge.py,summarise.py,rank.py,guards.py}
    pipeline.py  trace.py  cache.py
    server.py  static/{index.html,app.js,style.css}
    eval/{split.py,metrics.py,run.py,report.py}
  scripts/{bakeoff.py,record_traces.py,verify.py}
  tests/
```

## Data model

**Catalog record** (`catalog.jsonl`, one per movie): `movie_id` (MovieLens id), `tmdb_id`, `title`, `year`, `genres[]`, `overview` (non-empty), `director` (name), `cast[]` (top 5 billed names), `keywords[]`, `poster_path`, `first_rating_ts`, `n_ratings_train`.

**Graph:** undirected, weighted. Node types `movie`, `person`, `genre`, `keyword`. Edges: movie–director weight 3.0, movie–cast 2.0, movie–keyword 1.5, movie–genre 1.0 divided by log(1 + genre frequency) so common genres don't dominate.

**Trace** (one JSON per run, also streamed): `{run_id, mode, input, config, stages:[{name, started, ended, status, fallback_used, output}], candidates:[{movie_id, sources[], path}], final:[{movie_id, rank, reason, path, quote}], metrics:{llm_calls, seconds}}`.

## Pipeline contracts (typed with Pydantic)

- `understand(history: list[Rated], query: str|None) -> Profile{likes[], dislikes[], constraints[], mood, summary}`
- `retrieve(profile, history, query, config) -> list[Candidate{movie_id, sources, path, score}]` (≤50)
- `judge(profile, candidates) -> list[Verdict{movie_id, match: bool, fit: 0..1, reason}]` — batches of 10 candidates per model call.
- `summarise(profile, verdicts) -> Brief{strong[], violations[], notes}`
- `rank(profile, brief, candidates, k) -> list[Ranked{movie_id, reason}]`; guards then attach `path` and `quote`.

Per request: 1 + 5 + 1 + 1 = **8 model calls** (vs 200+ unbatched). Understanding results are cached by hash of (history, query).

## Retrieval details

- **Vector:** embed `profile.summary + query`; top 30 by cosine similarity from Chroma; exclude movies in history.
- **Graph:** seed nodes = viewer's most recent 20 movies rated ≥ 4 (feed) plus any catalog entities named in the query. Run personalized PageRank (damping 0.85) restricted to a 2-hop neighborhood; take the top 30 movie nodes not in history. Path for each = highest-weight chain from a seed (e.g. `Inception → Christopher Nolan → Interstellar`).
- **Hybrid:** union by `movie_id`, keep source tags (`vector`, `graph`, or both) and path, cap at 50 (interleave by rank so neither source starves).

## Guards (`guards.py`)

1. Drop any ranked id not in candidates. 2. Quote = the sentence of the movie's `overview` with highest word overlap with the reason; must be an exact substring (checked in code, not by the model). 3. Exclude history movies. 4. On two malformed outputs per stage, use fallback: judge → rank by retrieval score; rank → order by fit score.

## API

- `GET /api/health` → `{model_ready, catalog_size, graph_ready}`
- `GET /api/scenarios` → list of `{id, title, mode, blurb, cold_start}`
- `POST /api/recommend` body `{mode: "query"|"feed", query?, user_id?, retrieval: "vector"|"graph"|"hybrid", replay: bool, scenario_id?}` → SSE events `stage_start`, `stage_end`, `final`, `error`. 400 on empty input, 503 on model unavailable, 404 on unknown scenario.
- `GET /api/compare/{scenario_id}` → `{vector: Trace, hybrid: Trace}` (replay data)
- `GET /api/results` → evaluation tables from `demo/results/results.json`

## Evaluation protocol

- **Cutoff T** = (latest rating timestamp in data) − 12 months. Train = ratings before T; test = ratings at/after T.
- **Catalog** = movies with ≥ 50 train ratings ∪ movies whose first rating is ≥ T and have ≥ 3 ratings in the test period.
- **Cold-start item** = movie with 0 ratings before T.
- **Test viewers** = users with ≥ 20 train ratings and ≥ 1 rating ≥ 4 on a cold-start item in the test period. Sample 200 with a fixed seed. Ground truth = those cold-start items.
- **Metrics:** Recall@50 of the candidate set (no model calls, all test viewers), and end-to-end HitRate@5/10 and NDCG@5/10 (200 viewers × 3 configs). The ranker returns 10 in eval; the interface shows the first 5.
- **Configs:** (a) similarity-only = reproduced ARAG, (b) hybrid, (c) graph-only.
- **Resumability:** one JSONL line per finished (viewer, config); rerun skips completed pairs.
- **Cost:** model calls and wall-clock seconds per recommendation, averaged per config.

## Testing strategy

- **Unit:** metrics (hand-computed fixtures), split determinism, quote-substring guard, id-in-candidates guard, schema parsing with malformed fixtures, graph path construction on a 10-movie toy graph.
- **Integration:** pipeline with a **stub model client** returning canned valid / malformed / out-of-set outputs (runs in CI-like conditions without Ollama); API contract tests with the stub; replay endpoint serves every scenario.
- **End-to-end:** `make verify` runs a smoke test against the real model on 2 scenarios and the full replay set; fails on any acceptance criterion above that is automatable.
- **Coverage expectation:** ≥ 90% line coverage on `guards.py`, `metrics.py`, `split.py`; every acceptance criterion maps to at least one test.

## Security and performance constraints

- Server binds `127.0.0.1` only. TMDB key lives in `.env` (gitignored); never logged.
- Nothing is sent to any cloud model; after `make data` the demo works offline (posters fall back to a placeholder).
- Replay response < 1 s. Live hybrid run ≤ 90 s on the target machine, streaming stage progress throughout. If the bake-off shows > 90 s, reduce judge batch size/candidate cap before changing the model.
- Do not commit MovieLens files (license). Commit only derived demo artifacts (scenarios, traces, results).

---

# SECTION 3: TASKS

## Task 1: Scaffold, config, health check

**What to build:** Repo layout from the Plan, `Makefile` targets (`setup`, `data`, `index`, `demo`, `record`, `eval`, `verify`, `test`), `config.yaml` (model names, paths, k values, seeds), `.env.example` (TMDB_API_KEY), a `llm.py` stub, and `GET /api/health` returning `model_ready` by pinging the model server.
**Files likely affected:** `Makefile`, `config.yaml`, `requirements.txt`, `src/cinemind/{config.py,server.py}`, `.gitignore`
**Acceptance criteria:** 1) `make setup` creates the venv and installs requirements on a clean machine. 2) `make demo` starts a server on 127.0.0.1 and `/api/health` returns JSON. 3) `data/` and `.env` are gitignored.
**Dependencies:** none

## Task 2: Model bake-off

**What to build:** `scripts/bakeoff.py`: 24 hand-written test cases (profile text + movie description + expected match/no-match, deliberately including constraint violations like "no violence" vs a war film). For each of `gemma4:12b` and `qwen3.5:9b` (thinking disabled), batch 10 cases per call using the judge schema, and record: schema-valid rate, accuracy vs expected labels, seconds per call, and resident memory from `ollama ps`. Write `demo/results/bakeoff.md` and set `llm.model` in `config.yaml` to the winner (highest accuracy among models with ≥ 95% valid output; ties → faster).
**Files likely affected:** `scripts/bakeoff.py`, `src/cinemind/llm.py`, `config.yaml`, `demo/results/bakeoff.md`
**Acceptance criteria:** 1) Both models complete all 24 cases. 2) `bakeoff.md` contains the four measured numbers per model. 3) `config.yaml` names the winning model.
**Dependencies:** Task 1

## Task 3: Data download and TMDB fetch

**What to build:** `make data` step 1: download and unzip MovieLens 32M into `data/raw/`; parse ratings and links; **print the latest rating timestamp and fail with a clear message if it is less than 12 months after the earliest possible cutoff the config needs**. TMDB fetcher: for a list of tmdb ids, call the movie endpoint with credits and keywords appended, respect rate limits, retry with backoff, and checkpoint every 200 movies to `data/raw/tmdb/*.json` so reruns skip finished ids.
**Files likely affected:** `src/cinemind/data/{movielens.py,tmdb.py}`, `Makefile`
**Acceptance criteria:** 1) Rerunning after interruption fetches only missing ids. 2) Max rating date is printed. 3) A missing/invalid TMDB key produces a one-line error, not a stack trace.
**Dependencies:** Task 1

## Task 4: Catalog build

**What to build:** `build_catalog.py` applying the catalog rule from the Plan (cutoff T from the printed max timestamp), joining TMDB fields, dropping movies without an overview, writing `data/processed/catalog.jsonl` and a stats printout (count, how many cold-start, % with director/cast).
**Files likely affected:** `src/cinemind/data/build_catalog.py`, `tests/test_catalog.py`
**Acceptance criteria:** 1) Every record has non-empty `overview`, `director`, and ≥ 1 cast name or is dropped/logged. 2) Cold-start movie count printed and > 0. 3) Output is deterministic across two runs.
**Dependencies:** Task 3

## Task 5: Embeddings and vector index

**What to build:** `embed.py` embeds `"{title} ({year}). {overview} Genres: …"` with `nomic-embed-text` in batches, `make index` writes a persistent Chroma collection keyed by `movie_id`; `vector.py` with `search(text, k, exclude_ids) -> list[(movie_id, score)]`.
**Files likely affected:** `src/cinemind/retrieval/{embed.py,vector.py}`, `tests/test_vector.py`
**Acceptance criteria:** 1) Index count equals catalog count. 2) Searching "space exploration and time dilation" returns *Interstellar* in the top 10 (if in catalog). 3) `exclude_ids` are never returned.
**Dependencies:** Task 4

## Task 6: Knowledge graph and graph retrieval

**What to build:** `graph.py`: build the weighted graph from the catalog per the Plan and pickle it; `walk(seed_movie_ids, k, exclude_ids) -> list[(movie_id, score, path)]` using personalized PageRank limited to a 2-hop neighborhood; `path` is a readable chain string.
**Files likely affected:** `src/cinemind/retrieval/graph.py`, `tests/test_graph.py`
**Acceptance criteria:** 1) On a 10-movie toy graph, a movie sharing a director with the seed ranks above one sharing only a genre. 2) A cold-start movie with the seed's director is returned and its path names that director. 3) Seeds are never returned.
**Dependencies:** Task 4

## Task 7: Hybrid merge

**What to build:** `hybrid.py` with `retrieve(profile_text, query, seed_ids, history_ids, config) -> list[Candidate]` supporting `vector`, `graph`, `hybrid`; hybrid unions, de-duplicates, tags `sources`, interleaves by rank, caps at 50.
**Files likely affected:** `src/cinemind/retrieval/hybrid.py`, `src/cinemind/schemas.py`, `tests/test_hybrid.py`
**Acceptance criteria:** 1) Hybrid output has ≤ 50 unique ids. 2) A movie found by both sources shows both tags. 3) `vector` config never returns a graph-only movie and vice versa.
**Dependencies:** Tasks 5, 6

## Task 8: Model client with structured output

**What to build:** `llm.py`: `generate(prompt, schema) -> parsed object` calling the model server with a JSON schema, one retry on parse/validation failure, a stub implementation selectable by config for tests (canned valid / malformed / out-of-set modes), and counters for calls and seconds.
**Files likely affected:** `src/cinemind/llm.py`, `src/cinemind/schemas.py`, `tests/test_llm.py`
**Acceptance criteria:** 1) Malformed output once → retry succeeds and the call counter shows 2. 2) Malformed twice → raises a typed `StageFailed` error. 3) Stub mode runs with no model server.
**Dependencies:** Task 1

## Task 9: Agent 1 — Understanding

**What to build:** `understand.py` building a prompt from the viewer's most recent 30 rated movies (title, year, genres, rating) and the optional query; returns `Profile`. Works for query-only, history-only, and both. Cache by hash(history, query) in `cache.py` (JSON file).
**Files likely affected:** `src/cinemind/agents/understand.py`, `src/cinemind/cache.py`, `tests/test_understand.py`
**Acceptance criteria:** 1) With the stub, valid output parses to `Profile`. 2) Second identical call is a cache hit with zero model calls. 3) Empty history and empty query raises `EmptyInput`.
**Dependencies:** Task 8

## Task 10: Agent 2 — Batched judge

**What to build:** `judge.py`: split candidates into batches of 10; one model call per batch returning one `Verdict` per candidate; verify every candidate id is covered, re-ask once for missing ids, then apply fallback (retrieval-score order, `match` = top 40%) and flag `fallback_used`.
**Files likely affected:** `src/cinemind/agents/judge.py`, `tests/test_judge.py`
**Acceptance criteria:** 1) 50 candidates produce exactly 5 model calls and 50 verdicts. 2) A stub batch missing 2 ids triggers one re-ask. 3) Persistent failure yields verdicts with `fallback_used=true`, not an exception.
**Dependencies:** Task 8

## Task 11: Agents 3 and 4 and guards

**What to build:** `summarise.py` (one call → `Brief`), `rank.py` (one call → ordered list of `{movie_id, reason}` of length k), `guards.py` implementing the four guards from the Plan (id-in-candidates, history exclusion, extractive quote, fallbacks); fill short lists per the edge-case rule.
**Files likely affected:** `src/cinemind/agents/{summarise.py,rank.py,guards.py}`, `tests/test_guards.py`
**Acceptance criteria:** 1) A stub ranker output containing an id outside candidates is dropped and replaced. 2) Every attached `quote` is an exact substring of that movie's overview (test over 100 random movies). 3) Fewer than 5 matches still returns 5 items, weak ones labelled.
**Dependencies:** Tasks 7, 8

## Task 12: Pipeline orchestrator, events, traces

**What to build:** `pipeline.py` with `run(request, emit) -> Trace` executing understand → retrieve → judge → summarise → rank → guards, emitting `stage_start`/`stage_end` events with intermediate outputs, recording per-stage timing, fallback flags, call counts; `trace.py` to save/load traces as JSON.
**Files likely affected:** `src/cinemind/{pipeline.py,trace.py}`, `tests/test_pipeline.py`
**Acceptance criteria:** 1) With the stub, a full run produces a trace containing 4 agent stages plus retrieval. 2) Returned ids ⊆ candidate ids and ∩ history = ∅. 3) Trace JSON round-trips without loss.
**Dependencies:** Tasks 9, 10, 11

## Task 13: API server

**What to build:** FastAPI endpoints from the Plan (`/api/health`, `/api/scenarios`, `/api/recommend` as SSE, `/api/compare/{id}`, `/api/results`), error codes (400/404/503), replay serving from `demo/traces/`.
**Files likely affected:** `src/cinemind/server.py`, `tests/test_api.py`
**Acceptance criteria:** 1) Empty input → 400. 2) Unknown scenario → 404. 3) With model down, live request → 503 and replay request → 200.
**Dependencies:** Task 12

## Task 14: Demo interface

**What to build:** Single-page UI in `static/`: scenario cards (one click), free-text box, mode and retrieval selector, live stage timeline with expandable intermediate output, result cards (poster with placeholder fallback, reason, discovery path chip, evidence quote), "fallback used" and "replay" badges, comparison view with "only in hybrid" highlighting, and a Results tab with the evaluation table and a bar chart (drawn in plain SVG/canvas).
**Files likely affected:** `src/cinemind/static/{index.html,app.js,style.css}`
**Acceptance criteria:** 1) Clicking a scenario in replay mode renders 5 cards in < 1 s. 2) Comparison view marks hybrid-only movies. 3) Page works with no internet (placeholders instead of posters) and at 1280×720 without horizontal scrolling.
**Dependencies:** Task 13

## Task 15: Scenarios and recorded traces

**What to build:** `demo/scenarios.json` with ≥ 6 scenarios (≥ 2 query, ≥ 2 feed, ≥ 2 cold-start, each with a one-sentence blurb a non-technical viewer understands), `scripts/record_traces.py` (`make record`) running each scenario live in both `vector` and `hybrid`, saving traces to `demo/traces/`. Choose cold-start scenarios where hybrid surfaces at least one movie that similarity-only misses; if none can be found, record that honestly in the blurb.
**Files likely affected:** `demo/scenarios.json`, `scripts/record_traces.py`, `demo/traces/*.json`
**Acceptance criteria:** 1) Every scenario has both traces. 2) Replaying any scenario never calls the model (assert via counter). 3) Each cold-start scenario trace has `final` containing a movie with `n_ratings_train == 0`.
**Dependencies:** Tasks 12, 13

## Task 16: Evaluation split and metrics

**What to build:** `split.py` implementing the protocol (cutoff, catalog rule check, cold-start flag, viewer filter, seeded sample of 200), `metrics.py` (HitRate@k, NDCG@k with binary relevance, Recall@50), and a no-model script that computes Recall@50 for all three configs over **all** eligible test viewers.
**Files likely affected:** `src/cinemind/eval/{split.py,metrics.py}`, `tests/test_metrics.py`, `tests/test_split.py`
**Acceptance criteria:** 1) Metrics match hand-computed fixtures. 2) Split is byte-identical across two runs with the same seed. 3) No test viewer's ground-truth item appears in their train history.
**Dependencies:** Tasks 4, 7

## Task 17: End-to-end evaluation runner and report

**What to build:** `run.py` (`make eval`) running the full pipeline for 200 viewers × 3 configs with `rank` k=10, appending one JSONL line per (viewer, config) and skipping finished pairs on restart; `report.py` producing `demo/results/results.json` and `results.md` (HitRate@5/10, NDCG@5/10, Recall@50, model calls and seconds per recommendation, per config), plus a short error-analysis section listing 10 failures (viewer history summary, ground-truth movie, what each config returned).
**Files likely affected:** `src/cinemind/eval/{run.py,report.py}`, `demo/results/*`
**Acceptance criteria:** 1) Interrupt and restart processes only unfinished pairs; final tables equal an uninterrupted run. 2) Tables contain all three configs and all five metrics. 3) `results.md` states plainly whether hybrid beat similarity-only, including when it did not.
**Dependencies:** Tasks 12, 16

## Task 18: README, demo script, final verification

**What to build:** `README.md` (30-second pitch, architecture diagram as text, setup in ≤ 6 commands, how to demo in 3 minutes with a click-by-click script, how to reproduce evaluation, known limitations, ARAG citation), `scripts/verify.py` (`make verify`) that checks every automatable acceptance criterion (including both smoke runs against the real model) and prints PASS/FAIL per criterion.
**Files likely affected:** `README.md`, `scripts/verify.py`
**Acceptance criteria:** 1) `make verify` exits 0 on the final repo. 2) Following the README on a fresh clone reaches a working replay demo. 3) README lists the measured live latency from the bake-off/smoke run.
**Dependencies:** Tasks 14, 15, 17

## Review checkpoint

Before handing the task list to the coding agent, confirm the assumptions marked HIGH below (especially the model choice, the split cutoff, and the single-model design), and run `make data` once yourself to see the real max rating date.

---

# Assumptions to review

1. **Time-based split uses "latest rating − 12 months", not the document's "before 2024".** MovieLens 32M appears to end in 2023, which would make a "before 2024 / after 2024" split empty — Impact: HIGH
   Correct this if: your copy of the data has ratings in 2024 or later (Task 3 prints the real date).
2. **One model for all four agents (`gemma4:12b`, fallback `qwen3.5:9b`), picked by a bake-off on your machine.** Based on size-fit and published roundups, not a head-to-head I ran — Impact: HIGH
   Correct this if: the bake-off favors another model, or you accept swapping models mid-run (slower).
3. **Hybrid gain is not guaranteed.** The pipeline is content-based, so similarity retrieval is not starved of ratings for new movies; the measurable benefit is recall of relevant new movies in the candidate set — Impact: HIGH
   Correct this if: you want the claim fixed in advance; the report states results either way.
4. **Plain async pipeline instead of LangGraph** (flow is linear) — Impact: MEDIUM
   Correct this if: your faculty or the team expects LangGraph specifically; only `pipeline.py` changes.
5. **Catalog ≈ 8–12k movies** (≥ 50 train ratings, plus new movies with ≥ 3 test ratings), not all 87k — Impact: MEDIUM
   Correct this if: you need the full catalog (TMDB fetch and embedding time grow roughly 7×).
6. **Evaluation on a 200-viewer sample** for end-to-end metrics; Recall@50 over all eligible viewers — Impact: MEDIUM
   Correct this if: you have spare overnight compute for more (cost ≈ 8 model calls × 3 configs per viewer).
7. **Embeddings via `nomic-embed-text` in Ollama**, not a separate embedding library — Impact: MEDIUM
   Correct this if: you prefer sentence-transformers (adds a heavy dependency).
8. **Plain static frontend, no framework or build step** — Impact: LOW
   Correct this if: you want a React/Vite UI for portfolio reasons.
9. **Graph edge weights (director 3, cast 2, keyword 1.5, genre 1/log-frequency) and 2-hop PageRank are initial values**, not tuned — Impact: LOW
   Correct this if: error analysis shows a clear failure pattern.
10. **Raw MovieLens/TMDB data is not committed; only derived demo traces and results are** — Impact: LOW
    Correct this if: you obtain explicit redistribution permission.
11. **Live demo target ≤ 90 s per hybrid run on the M5/16 GB**; replay is the default for audiences — Impact: LOW
    Correct this if: the bake-off shows much faster or slower calls.