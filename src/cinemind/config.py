from pathlib import Path
from typing import Any, Dict, Optional
import os
import yaml
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class Config:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or (PROJECT_ROOT / "config.yaml")
        self._raw: Dict[str, Any] = {}
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._raw = yaml.safe_load(f) or {}

    @property
    def server_host(self) -> str:
        return self._raw.get("server", {}).get("host", "127.0.0.1")

    @property
    def server_port(self) -> int:
        return int(os.getenv("PORT", self._raw.get("server", {}).get("port", 8080)))

    @property
    def llm_model(self) -> str:
        return self._raw.get("llm", {}).get("model", "qwen3:8b")

    @property
    def embedding_model(self) -> str:
        return self._raw.get("llm", {}).get("embedding_model", "nomic-embed-text")

    @property
    def ollama_url(self) -> str:
        return os.getenv("OLLAMA_BASE_URL", self._raw.get("llm", {}).get("ollama_url", "http://127.0.0.1:11434"))

    @property
    def llm_stub(self) -> bool:
        return bool(self._raw.get("llm", {}).get("stub", False))

    @property
    def llm_timeout(self) -> float:
        return float(self._raw.get("llm", {}).get("timeout_seconds", 60.0))

    @property
    def vector_top_k(self) -> int:
        return int(self._raw.get("retrieval", {}).get("vector_top_k", 30))

    @property
    def graph_top_k(self) -> int:
        return int(self._raw.get("retrieval", {}).get("graph_top_k", 30))

    @property
    def hybrid_cap(self) -> int:
        return int(self._raw.get("retrieval", {}).get("hybrid_cap", 50))

    @property
    def graph_damping(self) -> float:
        return float(self._raw.get("retrieval", {}).get("graph_damping", 0.85))

    @property
    def graph_hops(self) -> int:
        return int(self._raw.get("retrieval", {}).get("graph_hops", 2))

    @property
    def final_k(self) -> int:
        return int(self._raw.get("ranking", {}).get("final_k", 5))

    @property
    def eval_k(self) -> int:
        return int(self._raw.get("ranking", {}).get("eval_k", 10))

    @property
    def catalog_path(self) -> Path:
        rel = self._raw.get("data", {}).get("catalog_path", "data/processed/catalog.jsonl")
        return PROJECT_ROOT / rel

    @property
    def graph_path(self) -> Path:
        rel = self._raw.get("data", {}).get("graph_path", "data/processed/graph.pkl")
        return PROJECT_ROOT / rel

    @property
    def vector_dir(self) -> Path:
        rel = self._raw.get("data", {}).get("vector_dir", "data/processed/chroma")
        return PROJECT_ROOT / rel

    @property
    def cache_path(self) -> Path:
        rel = self._raw.get("data", {}).get("cache_path", "data/processed/profile_cache.json")
        return PROJECT_ROOT / rel

    @property
    def scenarios_path(self) -> Path:
        rel = self._raw.get("data", {}).get("scenarios_path", "demo/scenarios.json")
        return PROJECT_ROOT / rel

    @property
    def traces_dir(self) -> Path:
        rel = self._raw.get("data", {}).get("traces_dir", "demo/traces")
        return PROJECT_ROOT / rel

    @property
    def results_path(self) -> Path:
        rel = self._raw.get("data", {}).get("results_path", "demo/results/results.json")
        return PROJECT_ROOT / rel

    @property
    def eval_checkpoint_path(self) -> Path:
        rel = self._raw.get("data", {}).get("eval_checkpoint_path", "demo/results/eval_checkpoint.jsonl")
        return PROJECT_ROOT / rel

    @property
    def tmdb_api_key(self) -> Optional[str]:
        return os.getenv("TMDB_API_KEY")

settings = Config()
