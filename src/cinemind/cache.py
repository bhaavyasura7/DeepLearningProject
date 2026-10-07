import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from src.cinemind.config import settings
from src.cinemind.schemas import Rated

class ProfileCache:
    def __init__(self, cache_path: Optional[Path] = None):
        self.cache_path = cache_path or settings.cache_path
        self._cache: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception:
                self._cache = {}

    def _save(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def compute_key(history: Optional[List[Rated]], query: Optional[str]) -> str:
        h_repr = []
        if history:
            for item in sorted(history, key=lambda x: x.movie_id):
                h_repr.append(f"{item.movie_id}:{item.rating}")
        q_repr = (query or "").strip().lower()
        raw_key = f"h={','.join(h_repr)}|q={q_repr}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self._cache.get(key)

    def set(self, key: str, value: Dict[str, Any]) -> None:
        self._cache[key] = value
        self._save()

    def clear(self) -> None:
        self._cache.clear()
        if self.cache_path.exists():
            try:
                self.cache_path.unlink()
            except Exception:
                pass
