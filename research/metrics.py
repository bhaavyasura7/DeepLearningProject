import math
from typing import List, Set, Any


def precision_at_k(recommended: List[Any], ground_truth: Set[Any], k: int = 10) -> float:
    """Calculates Precision@K.
    
    Precision@K = (# of relevant items in top K) / K
    """
    if k <= 0:
        return 0.0
    rec_k = recommended[:k]
    if not rec_k:
        return 0.0
    hits = sum(1 for item in rec_k if item in ground_truth)
    return round(hits / float(k), 4)


def recall_at_k(recommended: List[Any], ground_truth: Set[Any], k: int = 10) -> float:
    """Calculates Recall@K.
    
    Recall@K = (# of relevant items in top K) / (total relevant items)
    """
    if not ground_truth:
        return 0.0
    rec_k = recommended[:k]
    hits = sum(1 for item in rec_k if item in ground_truth)
    return round(hits / float(len(ground_truth)), 4)


def ndcg_at_k(recommended: List[Any], ground_truth: Set[Any], k: int = 10) -> float:
    """Calculates Normalized Discounted Cumulative Gain at K (binary relevance).
    
    DCG@K = sum_{i=1}^K (rel_i / log2(i + 1))
    IDCG@K = sum_{i=1}^{min(|ground_truth|, K)} (1 / log2(i + 1))
    NDCG@K = DCG@K / IDCG@K
    """
    if not ground_truth or k <= 0:
        return 0.0

    rec_k = recommended[:k]
    dcg = 0.0
    for idx, item in enumerate(rec_k):
        if item in ground_truth:
            dcg += 1.0 / math.log2(idx + 2)

    ideal_hits = min(len(ground_truth), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))

    if idcg == 0.0:
        return 0.0
    return round(dcg / idcg, 4)


def catalog_coverage(all_recommended_unique: Set[Any], total_catalog_size: int) -> float:
    """Catalog Coverage = (# unique items recommended) / (total catalog size)."""
    if total_catalog_size <= 0:
        return 0.0
    return round(len(all_recommended_unique) / float(total_catalog_size), 4)
