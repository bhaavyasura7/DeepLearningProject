"""Test-only environment: fixture catalog, toy indexes, stub model.

Nothing here is used by the application. The fixture catalog
(tests/fixtures/catalog.jsonl) holds ~200 real TMDB movie records; its
n_ratings_train values are fixture labels, not MovieLens counts. Embeddings use
a deterministic bag-of-words vector so tests run without Ollama.
"""

import asyncio
import hashlib
import json
import math
import shutil
import tempfile
from pathlib import Path
from typing import List

import numpy as np

from src.cinemind.config import settings, PROJECT_ROOT

FIXTURE_CATALOG = PROJECT_ROOT / "tests" / "fixtures" / "catalog.jsonl"


class BagOfWordsEmbedder:
    def __init__(self, dim: int = 384):
        self.dim = dim

    def embed_text(self, text: str) -> List[float]:
        vec = np.zeros(self.dim, dtype=np.float32)
        for w in text.lower().split():
            h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
            vec[h % self.dim] += 1.0 if (h >> 8) % 2 == 0 else -1.0
        n = np.linalg.norm(vec)
        return (vec / n if n else vec).tolist()

    def embed_batch(self, texts: List[str], batch_size: int = 64) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


_tmp = Path(tempfile.mkdtemp(prefix="cinemind-tests-"))
settings._raw.setdefault("data", {}).update({
    "catalog_path": str(_tmp / "catalog.jsonl"),
    "graph_path": str(_tmp / "graph.pkl"),
    "vector_dir": str(_tmp / "chroma"),
    "cache_path": str(_tmp / "profile_cache.json"),
    "traces_dir": str(_tmp / "traces"),
    "results_path": str(_tmp / "results" / "results.json"),
    "eval_checkpoint_path": str(_tmp / "results" / "eval_checkpoint.jsonl"),
})
shutil.copy(FIXTURE_CATALOG, settings.catalog_path)

import src.cinemind.retrieval.vector as _vector  # noqa: E402
_vector.EmbeddingService = BagOfWordsEmbedder
import src.cinemind.retrieval.embed as _embed  # noqa: E402
_embed.EmbeddingService = BagOfWordsEmbedder

from src.cinemind.data.build_catalog import load_catalog  # noqa: E402
from src.cinemind.retrieval.embed import build_vector_index  # noqa: E402
from src.cinemind.retrieval.graph import MovieGraph  # noqa: E402

build_vector_index(load_catalog(), settings.vector_dir, embedder=BagOfWordsEmbedder())
MovieGraph.build_from_catalog(load_catalog()).save(settings.graph_path)


def _record_fixture_traces() -> None:
    """Stub-model replay traces so replay endpoints can be tested."""
    from src.cinemind.llm import LLMClient
    from src.cinemind.pipeline import Pipeline
    from src.cinemind.schemas import RecommendRequest, Rated
    from src.cinemind.trace import TraceManager

    tm = TraceManager()
    pipe = Pipeline(llm=LLMClient(stub=True))
    for sc in json.loads(settings.scenarios_path.read_text(encoding="utf-8")):
        for cfg in ("vector", "hybrid"):
            req = RecommendRequest(mode=sc["mode"], query=sc.get("query"),
                                   history=[Rated(**h) for h in sc.get("history") or []],
                                   retrieval=cfg, scenario_id=sc["id"])
            tm.save_trace(asyncio.run(pipe.run(req)), filename=f"{sc['id']}_{cfg}.json")


_record_fixture_traces()


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_tmp, ignore_errors=True)
