import math
from typing import List, Set, Union

def hit_rate_at_k(
    recommended_ids: List[int],
    ground_truth_ids: Union[Set[int], List[int]],
    k: int = 5
) -> float:
    """Returns 1.0 if at least one ground-truth item is in the top k recommendations, else 0.0."""
    gt_set = set(ground_truth_ids)
    if not gt_set:
        return 0.0
    top_k = set(recommended_ids[:k])
    return 1.0 if bool(top_k.intersection(gt_set)) else 0.0

def ndcg_at_k(
    recommended_ids: List[int],
    ground_truth_ids: Union[Set[int], List[int]],
    k: int = 5
) -> float:
    """
    Computes Normalized Discounted Cumulative Gain at rank k with binary relevance.
    DCG = sum_{i=1}^k (rel_i / log2(i + 1))
    IDCG = sum_{i=1}^{min(|GT|, k)} (1 / log2(i + 1))
    """
    gt_set = set(ground_truth_ids)
    if not gt_set:
        return 0.0

    dcg = 0.0
    for idx, mid in enumerate(recommended_ids[:k], start=1):
        if mid in gt_set:
            dcg += 1.0 / math.log2(idx + 1)

    idcg = 0.0
    max_relevant = min(len(gt_set), k)
    for idx in range(1, max_relevant + 1):
        idcg += 1.0 / math.log2(idx + 1)

    if idcg <= 0.0:
        return 0.0

    return dcg / idcg

def recall_at_k(
    candidate_ids: List[int],
    ground_truth_ids: Union[Set[int], List[int]],
    k: int = 50
) -> float:
    """Computes Recall@k: |candidates[:k] ∩ GT| / |GT|."""
    gt_set = set(ground_truth_ids)
    if not gt_set:
        return 0.0
    cand_set = set(candidate_ids[:k])
    found = len(cand_set.intersection(gt_set))
    return found / len(gt_set)
