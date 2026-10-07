import re
from typing import List, Set, Dict, Optional, Tuple
from src.cinemind.schemas import Candidate, Verdict, RankedItem, RankedOutputItem

def split_into_sentences(text: str) -> List[str]:
    """Splits text into sentences while preserving exact substring representations."""
    if not text:
        return []
    # Pattern splitting on sentence terminators (. ! ?)
    raw_sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in raw_sentences if s.strip()]
    return sentences or [text.strip()]

def extract_evidence_quote(overview: str, reason: str) -> str:
    """
    Finds the sentence of movie's overview with highest word overlap with reason.
    Guarantees quote is an EXACT substring of overview.
    """
    if not overview or not overview.strip():
        return ""

    sentences = split_into_sentences(overview)
    if not sentences:
        return overview

    # Tokenize reason words for matching
    reason_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', reason.lower()))
    if not reason_words:
        # Default to first sentence
        return sentences[0]

    best_sentence = sentences[0]
    best_score = -1

    for s in sentences:
        s_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', s.lower()))
        overlap = len(reason_words.intersection(s_words))
        if overlap > best_score:
            best_score = overlap
            best_sentence = s

    # Ensure exact substring match in overview
    if best_sentence in overview:
        return best_sentence
    # Fallback to whole overview or first sentence if somehow not exact
    for s in sentences:
        if s in overview:
            return s
    return overview

class Guards:
    @staticmethod
    def apply_guards(
        rankings: List[RankedOutputItem],
        candidates: List[Candidate],
        verdicts: List[Verdict],
        history_ids: Optional[Set[int]] = None,
        k: int = 5
    ) -> List[RankedItem]:
        """
        Applies all 4 spec guards + edge-case rules:
        1. Drops any ID outside candidates or in history.
        2. Fills missing slots up to k using verdict fit scores (matches first, then highest fit weak matches).
        3. Attaches exact extractive quotes, graph paths, poster paths, and weak-match flags.
        """
        exclude_set = set(history_ids or set())
        cand_map: Dict[int, Candidate] = {c.movie_id: c for c in candidates}
        verdict_map: Dict[int, Verdict] = {v.movie_id: v for v in verdicts}

        seen_ids: Set[int] = set()
        validated_items: List[Tuple[int, str, bool]] = []  # (movie_id, reason, is_weak)

        # 1. Process ranked items from model
        for item in rankings:
            mid = item.movie_id
            # Guard 1: Drop if outside candidates
            if mid not in cand_map:
                continue
            # Guard 2: Drop if in history
            if mid in exclude_set:
                continue
            if mid in seen_ids:
                continue

            seen_ids.add(mid)
            v = verdict_map.get(mid)
            is_weak = (v is not None and not v.match)
            validated_items.append((mid, item.reason, is_weak))
            if len(validated_items) >= k:
                break

        # 2. Fill short lists if fewer than k items
        if len(validated_items) < k:
            # Candidates judged match sorted by fit
            matched_verdicts = [v for v in verdicts if v.match and v.movie_id in cand_map and v.movie_id not in seen_ids and v.movie_id not in exclude_set]
            matched_verdicts.sort(key=lambda v: v.fit, reverse=True)

            for v in matched_verdicts:
                seen_ids.add(v.movie_id)
                validated_items.append((v.movie_id, v.reason, False))
                if len(validated_items) >= k:
                    break

        if len(validated_items) < k:
            # Non-matched candidates sorted by fit (weak matches)
            unmatched_verdicts = [v for v in verdicts if not v.match and v.movie_id in cand_map and v.movie_id not in seen_ids and v.movie_id not in exclude_set]
            unmatched_verdicts.sort(key=lambda v: v.fit, reverse=True)

            for v in unmatched_verdicts:
                seen_ids.add(v.movie_id)
                validated_items.append((v.movie_id, f"Weak match: {v.reason}", True))
                if len(validated_items) >= k:
                    break

        # 3. Construct final RankedItem objects with attached attributes
        final_ranked: List[RankedItem] = []
        for rank_idx, (mid, reason, is_weak) in enumerate(validated_items[:k], start=1):
            cand = cand_map[mid]
            v = verdict_map.get(mid)
            quote = extract_evidence_quote(cand.overview or "", reason)

            item = RankedItem(
                movie_id=mid,
                rank=rank_idx,
                title=cand.title,
                year=cand.year,
                reason=reason,
                path=cand.path,
                quote=quote,
                overview=cand.overview,
                is_weak_match=is_weak,
                sources=cand.sources,
                fit=v.fit if v else cand.score
            )
            final_ranked.append(item)

        return final_ranked
