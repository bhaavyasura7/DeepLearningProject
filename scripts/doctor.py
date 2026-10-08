"""`make doctor`: plain-English checklist of what is ready and what to run next."""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import httpx

from src.cinemind.config import settings
from src.cinemind.data import movielens

OK, NO = "\033[92m✓\033[0m", "\033[91m✗\033[0m"
todo = []


def line(ok: bool, text: str, fix: str = "") -> None:
    print(f"  {OK if ok else NO} {text}")
    if not ok and fix and fix not in todo:
        todo.append(fix)


def main() -> int:
    print("\nCineMind readiness check\n")

    line(bool(settings.tmdb_api_key) or settings.catalog_path.exists(),
         "TMDB API key in .env (needed once, for `make data`)",
         "Put your TMDB key in .env:  cp .env.example .env  then edit TMDB_API_KEY")

    tags = []
    try:
        tags = [m["name"] for m in httpx.get(f"{settings.ollama_url}/api/tags", timeout=3).json().get("models", [])]
        line(True, f"Ollama is running at {settings.ollama_url}")
    except Exception:
        line(False, f"Ollama is running at {settings.ollama_url}", "Install and start Ollama: https://ollama.com  (then `ollama serve`)")
    has = lambda name: name in tags or f"{name}:latest" in tags
    line(has(settings.llm_model), f"AI model `{settings.llm_model}` pulled", "make models")
    line(has(settings.embedding_model), f"Embedding model `{settings.embedding_model}` pulled", "make models")

    line(movielens.zip_path().exists(), "MovieLens 32M ratings downloaded", "make data")
    n = 0
    if settings.catalog_path.exists():
        movies = [json.loads(l) for l in settings.catalog_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        n = len(movies)
        cold = sum(1 for m in movies if m["n_ratings_train"] == 0)
        line(True, f"Catalog built: {n:,} movies, {cold:,} brand-new (0 ratings before the cut-off)")
    else:
        line(False, "Catalog built", "make data")

    count = 0
    if settings.vector_dir.exists():
        try:
            import chromadb
            count = chromadb.PersistentClient(path=str(settings.vector_dir)).get_collection("cinemind_movies").count()
        except Exception:
            count = 0
    line(n > 0 and count == n, f"Text-similarity index built ({count:,} movies)", "make index")
    line(settings.graph_path.exists(), "Movie graph built", "make index")

    scenarios = json.loads(settings.scenarios_path.read_text(encoding="utf-8"))
    unbound = [s["id"] for s in scenarios if s.get("select") and not s.get("user_id")]
    line(not unbound, "Examples use real MovieLens viewers", "make scenarios")
    missing = [f"{s['id']}_{c}" for s in scenarios for c in ("vector", "hybrid")
               if not (settings.traces_dir / f"{s['id']}_{c}.json").exists()]
    line(not missing, f"Saved runs recorded ({2 * len(scenarios) - len(missing)}/{2 * len(scenarios)})", "make record")
    line(settings.results_path.exists(), "Evaluation results generated", "make eval")

    print()
    if todo:
        print("Next steps, in order:")
        for i, t in enumerate(todo, 1):
            print(f"  {i}. {t}")
        print("\nThen start the app with:  make demo   →  http://127.0.0.1:8080\n")
        return 1
    print("Everything is ready.  make demo   →  http://127.0.0.1:8080\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
