from typing import List, Tuple, Optional, Set, Dict
from src.cinemind.agents.guards import Guards
from src.cinemind.llm import LLMClient, default_llm
from src.cinemind.schemas import Profile, Brief, Candidate, Verdict, RankedItem, RankModelOutput, RankedOutputItem

class RankingAgent:
    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or default_llm

    async def rank(
        self,
        profile: Profile,
        brief: Brief,
        candidates: List[Candidate],
        verdicts: List[Verdict],
        k: int = 5,
        history_ids: Optional[Set[int]] = None
    ) -> Tuple[List[RankedItem], bool]:
        """
        Ranks top k recommendations using the Profile, Brief, and Verdicts.
        Guards ensure:
        - Only candidates are returned.
        - History is excluded.
        - Verbatim quotes and paths are attached.
        - Short lists are filled with labeled weak matches.
        """
        cand_map: Dict[int, Candidate] = {c.movie_id: c for c in candidates}
        verdict_map: Dict[int, Verdict] = {v.movie_id: v for v in verdicts}
        fallback_used = False

        prompt = (
            "You are the final Ranking stage of CineMind.\n"
            "Select and order the top movie recommendations for the viewer based on their profile, brief, and judged verdicts.\n\n"
            f"PROFILE SUMMARY: {profile.summary}\n"
            f"BRIEF NOTES: {brief.notes}\n"
            f"STANDOUT CANDIDATES: {', '.join(brief.strong)}\n\n"
            "CANDIDATES WITH VERDICTS:\n"
        )

        # Show candidates that matched first
        matched_candidates = [c for c in candidates if verdict_map.get(c.movie_id) and verdict_map[c.movie_id].match]
        matched_candidates.sort(key=lambda c: verdict_map[c.movie_id].fit, reverse=True)

        for c in matched_candidates[:15]:
            v = verdict_map[c.movie_id]
            prompt += f"- ID {c.movie_id}: {c.title} ({c.year}) | Fit: {v.fit:.2f} | Reason: {v.reason}\n"

        prompt += (
            f"\nReturn a valid JSON object matching RankModelOutput with 'rankings': list of exactly {k} items.\n"
            "Each item must have 'movie_id' (must be one of the listed candidate IDs) and 'reason' (compelling personalized explanation)."
        )

        raw_rankings: List[RankedOutputItem] = []
        try:
            res: RankModelOutput = await self.llm.generate(prompt, RankModelOutput)
            raw_rankings = res.rankings
        except Exception:
            # Deterministic fallback: order by fit score descending
            fallback_used = True
            sorted_verdicts = sorted(verdicts, key=lambda v: (v.match, v.fit), reverse=True)
            for v in sorted_verdicts[:k]:
                raw_rankings.append(RankedOutputItem(
                    movie_id=v.movie_id,
                    reason=f"Top recommendation selected based on fit score ({v.fit:.2f}): {v.reason}"
                ))

        # Apply Guards
        final_items = Guards.apply_guards(
            rankings=raw_rankings,
            candidates=candidates,
            verdicts=verdicts,
            history_ids=history_ids,
            k=k
        )

        return final_items, fallback_used
