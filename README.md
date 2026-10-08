# CineMind

**Movie recommendations that explain themselves, and can find brand-new films.**

You type what you want (or give a viewer's rating history). A local AI model reads it, looks through real movies, and returns **5 picks**. Each pick says **why** it fits, **how it was found**, and quotes the movie's own description **word for word** as evidence.

The research question: rating-based recommenders can't suggest a film nobody has rated yet. CineMind adds a **movie graph** (shared directors, actors, genres) next to normal **text similarity**. If you loved *Inception*, the graph reaches *Oppenheimer* through "Director: Christopher Nolan" even when it has zero ratings. We measure whether that helps on real MovieLens viewers.

It reproduces the 4-agent design of **ARAG** (Maragheh et al., 2025, *ARAG: Agentic Retrieval Augmented Generation for Personalized Recommendation*) and extends its candidate retrieval with graph search.

---

## How it works

```
 request / rating history
          │
 1. Understand ── AI writes likes, dislikes, rules ("no horror")
          │
 2. Find candidates (≤ 50)
      ├─ text similarity: nomic-embed-text + Chroma, top 30
      └─ movie graph:     Personalized PageRank (2 hops, α=0.85) from liked / named movies, top 30
          │
 3. Judge ─────── AI scores every candidate 0–1 with a reason (10 per call)
 4. Summarise ─── AI writes a short brief
 5. Rank ──────── AI picks 5
          │
 Checks in code: only real candidates, no already-watched movies, quotes are exact substrings
```

About 8 AI calls per request. Every step streams to the UI. If the AI returns bad output twice, a simple backup rule runs and the UI marks the step **backup rule used**.

Three retrieval settings can be compared: **text similarity only** (the ARAG baseline), **movie graph only**, and **both** (ours).

---

## Setup

You need Python 3.11 with [uv](https://docs.astral.sh/uv/), [Ollama](https://ollama.com), and a free [TMDB API key](https://www.themoviedb.org/settings/api). It's built for an Apple Silicon Mac with 16 GB of RAM, and Linux works too.

```bash
make setup                         # Python environment
cp .env.example .env               # then put your TMDB key in .env
make models                        # ollama pull qwen3:8b + nomic-embed-text
make data index scenarios          # MovieLens 32M + TMDB catalog, embeddings, graph, real demo viewers
make record eval                   # saved runs for the demo + evaluation (slow: uses the real model)
make demo                          # → http://127.0.0.1:8080
```

At any point, **`make doctor`** prints what is ready and what to run next.

| Command | What it does |
|---|---|
| `make data` | Downloads MovieLens 32M, fetches TMDB metadata (resumable), builds the catalog. Cut-off = latest rating − 12 months. Catalog = movies with ≥ 50 ratings before the cut-off, plus movies first rated after it with ≥ 3 ratings. Movies with no description, director or cast are dropped. |
| `make index` | Embeds every movie with `nomic-embed-text` (Chroma) and builds the movie graph (NetworkX). |
| `make scenarios` | Ties the viewer examples to **real MovieLens users**, using their real ratings from before the cut-off. The new-movie examples use a user who really rated that new film 4★+ after the cut-off. |
| `make record` | Runs every example with the real AI (text-only and both) and saves the runs for instant replay. |
| `make eval` | Builds the real-viewer test split, runs 200 viewers × 3 settings, computes candidate recall over **all** eligible viewers, and writes `demo/results/results.{json,md}`. Resumable. |
| `make bakeoff` | 24 hand-written judge cases on two models: schema validity, accuracy, seconds per call. |
| `make verify` | Checks the spec's acceptance criteria against the real data, the saved runs and a live run. |
| `make test` | Unit and integration tests, no Ollama or data needed. |

Once `make data` has run, everything works offline. Posters load from TMDB when online and show initials otherwise.

---

## Demo

See **[DEMO.md](DEMO.md)** for a 3-minute click-by-click script.

---

## Evaluation

* **Split:** time-based. Ratings before the cut-off are history; ratings after it are the future.
* **New movie (cold-start):** a film with 0 ratings before the cut-off.
* **Test viewers:** real MovieLens users with ≥ 20 ratings before the cut-off who rated at least one new movie 4★+ after it. 200 are sampled with a fixed seed. Ground truth is those new movies.
* **Metrics:** HitRate@5/10 and NDCG@5/10 (end to end, AI returns 10), Recall@50 of the candidate list, plus AI calls and seconds per request.

Results are written by `make eval` to `demo/results/results.md` and shown in the app's **Results** tab. The report states plainly whether "both" beat "text similarity only", including when it did not. No results are committed until they have been produced on real data.

---

## Repository

```
src/cinemind/
  data/        movielens.py · tmdb.py · build_catalog.py
  retrieval/   embed.py · vector.py · graph.py · hybrid.py
  agents/      understand.py · judge.py · summarise.py · rank.py · guards.py
  eval/        split.py · run.py · recall.py · metrics.py · report.py
  pipeline.py  server.py  llm.py  schemas.py  trace.py  cache.py  config.py
  static/      index.html · app.js · style.css   (no build step)
scripts/       doctor.py · pick_scenario_users.py · record_traces.py · bakeoff.py · verify.py
demo/          scenarios.json · traces/ (saved runs) · results/
tests/         pytest suite + tiny fixtures (the only place a stub model is used)
spec.md        full specification
```

## Notes and limits

* MovieLens and TMDB data are never committed (license). Only derived demo files are.
* The stub AI client and the small fixture catalog exist only for the test suite. The app, `make record` and `make eval` always use the real model and refuse to run without it.
* Graph edge weights (director 3, cast 2, keyword 1.5, genre 1/log(1+frequency)) are initial values, not tuned.
* Text similarity works from descriptions, so new movies are not invisible to it. The graph's measurable benefit is getting the right new movie into the candidate list; the eval reports whether that happens.
