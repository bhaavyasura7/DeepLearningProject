import json
import pytest
from pathlib import Path
from src.cinemind.eval.run import run_evaluation
from src.cinemind.config import settings

@pytest.mark.asyncio
async def test_evaluation_resumability(tmp_path: Path, monkeypatch):
    test_cp = tmp_path / "test_checkpoint.jsonl"
    settings._raw["data"]["eval_checkpoint_path"] = str(test_cp)

    # 1. Run for 5 viewers
    await run_evaluation(num_viewers=5, configs=["vector"])
    assert test_cp.exists()

    with open(test_cp, "r") as f:
        lines = [line.strip() for line in f if line.strip()]
    assert len(lines) == 5

    # 2. Run again for 10 viewers (should process only 5 remaining viewers, not reprocess first 5)
    await run_evaluation(num_viewers=10, configs=["vector"])

    with open(test_cp, "r") as f:
        lines2 = [line.strip() for line in f if line.strip()]
    assert len(lines2) == 10
