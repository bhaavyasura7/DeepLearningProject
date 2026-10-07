import pytest
from pathlib import Path
from src.cinemind.eval.split import EvalSplitBuilder

def test_split_determinism_and_leakage(tmp_path: Path):
    path1 = tmp_path / "split1.json"
    path2 = tmp_path / "split2.json"

    builder = EvalSplitBuilder(seed=42)
    viewers1 = builder.build_split(num_viewers=50, output_file=path1)
    viewers2 = builder.build_split(num_viewers=50, output_file=path2)

    # 1. Byte-identical across two runs
    with open(path1, "rb") as f1, open(path2, "rb") as f2:
        assert f1.read() == f2.read()

    # 2. No test viewer's ground-truth item appears in their train history
    for v in viewers1:
        train_mids = {r["movie_id"] for r in v["train_history"]}
        gt_ids = set(v["ground_truth_ids"])
        assert len(gt_ids) > 0
        assert len(train_mids) >= 20
        assert len(train_mids.intersection(gt_ids)) == 0, f"Leakage found for user {v['user_id']}"
