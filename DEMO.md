# 3-minute demo script

**Before the meeting:** run `make doctor`. It should say *Everything is ready*. Then run `make demo` and open http://127.0.0.1:8080.
Leave **Run → Saved run** selected. The demo then works with no internet and no AI model running. If Ollama is running, you can also show a live run at the end.

---

### 0:00 · The idea (Try it tab, top of the page)

> "This recommends movies and explains every pick. Each card shows *why*, *how the movie was found*, and an exact quote from the film's description. The quote is copied by code, not written by the AI, so it can't be made up.
> The research question: normal recommenders can't suggest a film nobody has rated yet. I add a **movie graph** of directors, actors and genres to normal text search, to see if it finds those new films."

### 0:30 · A real viewer and a brand-new film

Click the example **New movie: Nolan fan → Oppenheimer?**.

* Point at the grey box: *"This is a real MovieLens user. These are their real ratings before the cut-off date. After the cut-off they rated **Oppenheimer** 4★ or more, and Oppenheimer had **zero** ratings before that."*
* Point at the 5 steps lighting up: *"Understand → find candidates → judge each → summarise → pick 5."*
* In the results, look for the tags **New movie · 0 ratings before cut-off** and **✓ This viewer really loved it**.
  Point at **Found by**, e.g. `Interstellar → Director: Christopher Nolan → Oppenheimer`.
* Open **Show what each step produced**. Here you can show the profile the AI wrote, the 50 candidates and how each was found, and the AI's score and reason for every one.

### 1:30 · Same example, with and without the graph

Click **Graph vs no graph** at the top and choose the same example.

> "Left is the baseline from the ARAG paper: text similarity only. Right is mine. Anything tagged **Found only with graph** is a movie the baseline missed."

### 2:00 · The numbers

Click **Results**.

> "I hid the last 12 months of ratings and asked: for 200 real viewers, does the system recommend the new movies they really went on to love?
> *Hit in top 5* is the share of viewers where that happened. *In candidates* is whether the right movie even made the 50-movie shortlist."

Read the blue sentence aloud. It says honestly whether the graph helped.

### 2:30 · Trust and failure handling (How it works tab)

> "Three checks are in code, not the AI: a pick must be a real candidate, watched movies are removed, and quotes are exact. If the AI returns broken output twice, a simple rule takes over and the page shows **backup rule used**. It never hides that."

### Optional: live run (only if Ollama is running)

Select **Run → Live AI** and type `fun sci-fi like Inception but shorter`. The steps fill in live (about a minute on a 16 GB Mac).
The status pill in the top-right shows whether the AI is ready.

---

**Likely questions**

* *Is the data real?* Yes. MovieLens 32M ratings and TMDB descriptions. The examples are real users chosen by `make scenarios`, and the rules for choosing them are in `demo/scenarios.json`.
* *Which AI?* A local model through Ollama (`qwen3:8b` by default, see `config.yaml`). Nothing is sent to the cloud.
* *Is it reproducible?* Fixed seed. The split is byte-identical across runs, and `make verify` checks the acceptance criteria.
