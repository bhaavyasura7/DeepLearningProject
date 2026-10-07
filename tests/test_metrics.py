import math
import pytest
from src.cinemind.eval.metrics import hit_rate_at_k, ndcg_at_k, recall_at_k

def test_hand_computed_metric_fixtures():
    # Ground truth: {10, 20}
    gt = {10, 20}

    # Case 1: GT item 10 at rank 1, GT item 20 at rank 3
    # recs = [10, 99, 20, 55, 66]
    recs = [10, 99, 20, 55, 66]

    # HitRate@5: 1.0
    assert hit_rate_at_k(recs, gt, k=5) == 1.0
    # HitRate@1: 1.0
    assert hit_rate_at_k(recs, gt, k=1) == 1.0
    # HitRate@1 with miss
    assert hit_rate_at_k([99, 10], gt, k=1) == 0.0

    # NDCG@5 hand calculation:
    # rank 1 (mid 10): 1 / log2(2) = 1.0
    # rank 2 (mid 99): 0
    # rank 3 (mid 20): 1 / log2(4) = 0.5
    # DCG = 1.0 + 0.5 = 1.5
    # IDCG (2 relevant items in top 2):
    # rank 1: 1 / log2(2) = 1.0
    # rank 2: 1 / log2(3) = 1 / 1.5849625 = 0.63092975
    # IDCG = 1.0 + 0.63092975 = 1.63092975
    # NDCG = 1.5 / 1.63092975 = 0.91972...
    expected_ndcg = 1.5 / (1.0 + (1.0 / math.log2(3)))
    computed_ndcg = ndcg_at_k(recs, gt, k=5)
    assert pytest.approx(computed_ndcg, rel=1e-4) == expected_ndcg

    # Case 2: Complete miss
    miss_recs = [99, 88, 77, 66, 55]
    assert hit_rate_at_k(miss_recs, gt, k=5) == 0.0
    assert ndcg_at_k(miss_recs, gt, k=5) == 0.0

    # Recall@50
    # 2 items in candidate set, both in GT -> Recall = 2 / 2 = 1.0
    assert recall_at_k(recs, gt, k=50) == 1.0
    # 1 item in candidates -> Recall = 1 / 2 = 0.5
    assert recall_at_k([10, 88, 99], gt, k=50) == 0.5
