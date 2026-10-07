import json
from pathlib import Path
from typing import Optional
from src.cinemind.config import settings
from src.cinemind.schemas import Trace

class TraceManager:
    def __init__(self, traces_dir: Optional[Path] = None):
        self.traces_dir = traces_dir or settings.traces_dir
        self.traces_dir.mkdir(parents=True, exist_ok=True)

    def save_trace(self, trace: Trace, filename: Optional[str] = None) -> Path:
        name = filename or f"{trace.run_id}_{trace.config}.json"
        path = self.traces_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(trace.model_dump(), f, indent=2, ensure_ascii=False)
        return path

    def load_trace(self, path: Path) -> Trace:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Trace.model_validate(data)

    def get_scenario_trace(self, scenario_id: str, config: str = "hybrid") -> Optional[Trace]:
        target = self.traces_dir / f"{scenario_id}_{config}.json"
        if target.exists():
            return self.load_trace(target)
        # Try generic scenario_id.json
        alt = self.traces_dir / f"{scenario_id}.json"
        if alt.exists():
            return self.load_trace(alt)
        return None

default_trace_manager = TraceManager()
