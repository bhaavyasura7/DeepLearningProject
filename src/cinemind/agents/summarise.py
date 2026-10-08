from typing import List, Tuple, Optional, Dict
from src.cinemind.llm import LLMClient, default_llm
from src.cinemind.schemas import Profile, Verdict, Candidate, Brief

class SummarisingAgent:
    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or default_llm

    async def summarise(
        self,
        profile: Profile,
        verdicts: List[Verdict],
        candidates: List[Candidate],
        allow_fallback: bool = True
    ) -> Tuple[Brief, bool]:
        """
        Compresses judgements into a coherent Brief highlighting strong matches and key violations.
        """
        cand_map: Dict[int, Candidate] = {c.movie_id: c for c in candidates}
        matched = [v for v in verdicts if v.match]
        rejected = [v for v in verdicts if not v.match]

        matched.sort(key=lambda v: v.fit, reverse=True)
        rejected.sort(key=lambda v: v.fit)

        # Build prompt
        prompt = (
            "You are the Summarising stage of CineMind.\n"
            "Synthesize the individual movie evaluations into a concise Brief for the ranking stage.\n\n"
            f"USER PROFILE:\n- Summary: {profile.summary}\n- Likes: {', '.join(profile.likes)}\n- Constraints: {', '.join(profile.constraints)}\n\n"
            "STANDOUT MATCHES:\n"
        )
        for v in matched[:10]:
            c = cand_map.get(v.movie_id)
            title = c.title if c else f"Movie {v.movie_id}"
            prompt += f"- {title} (Fit {v.fit:.2f}): {v.reason}\n"

        prompt += "\nNOTABLE REJECTIONS / CONSTRAINT VIOLATIONS:\n"
        for v in rejected[:8]:
            c = cand_map.get(v.movie_id)
            title = c.title if c else f"Movie {v.movie_id}"
            prompt += f"- {title} (Fit {v.fit:.2f}): {v.reason}\n"

        prompt += (
            "\nProduce a valid JSON object matching the Brief schema with:\n"
            "- strong: list of movie titles representing top standout options\n"
            "- violations: list of movie titles that were rejected due to preferences or constraints\n"
            "- notes: 1-2 sentence overview of recommendation landscape\n"
        )

        try:
            brief: Brief = await self.llm.generate(prompt, Brief)
            return brief, False
        except Exception as e:
            if not allow_fallback:
                raise e
            # Deterministic fallback brief
            strong_titles = []
            for v in matched[:5]:
                c = cand_map.get(v.movie_id)
                strong_titles.append(c.title if c and c.title else f"Movie {v.movie_id}")

            violation_titles = []
            for v in rejected[:5]:
                c = cand_map.get(v.movie_id)
                violation_titles.append(c.title if c and c.title else f"Movie {v.movie_id}")

            fallback_brief = Brief(
                strong=strong_titles,
                violations=violation_titles,
                notes="Deterministic brief generated directly from verdict fit scores and constraints."
            )
            return fallback_brief, True
