import math
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from research.metrics import precision_at_k, recall_at_k, ndcg_at_k, catalog_coverage


def test_hand_checkable_metrics():
    recommended = [10, 20, 30, 40, 50]
    ground_truth = {20, 40}

    # K = 5
    assert precision_at_k(recommended, ground_truth, k=5) == 0.4
    assert recall_at_k(recommended, ground_truth, k=5) == 1.0

    # Hand calculation for NDCG@5:
    # item 20 is at index 1: gain = 1 / log2(3) = 0.6309297
    # item 40 is at index 3: gain = 1 / log2(5) = 0.4306765
    # DCG = 0.6309297 + 0.4306765 = 1.061606
    # IDCG with 2 items: 1/log2(2) + 1/log2(3) = 1.0 + 0.6309297 = 1.6309297
    # NDCG = 1.061606 / 1.6309297 = 0.6509
    expected_ndcg = round(
        (1.0 / math.log2(3) + 1.0 / math.log2(5)) / (1.0 / math.log2(2) + 1.0 / math.log2(3)),
        4
    )
    assert ndcg_at_k(recommended, ground_truth, k=5) == expected_ndcg

    # K = 2: recommended[:2] = [10, 20] -> 1 hit
    assert precision_at_k(recommended, ground_truth, k=2) == 0.5
    assert recall_at_k(recommended, ground_truth, k=2) == 0.5


def test_catalog_coverage():
    unique_items = {1, 2, 3, 4}
    assert catalog_coverage(unique_items, 10) == 0.4
    assert catalog_coverage(set(), 10) == 0.0
