from typing import List, Tuple, Dict, Set, Optional
from src.cinemind.llm import LLMClient, default_llm, StageFailed
from src.cinemind.schemas import Profile, Candidate, Verdict, JudgeBatchOutput

class JudgingAgent:
    def __init__(self, llm: Optional[LLMClient] = None, batch_size: int = 10):
        self.llm = llm or default_llm
        self.batch_size = batch_size

    async def judge_batch(
        self,
        profile: Profile,
        batch: List[Candidate]
    ) -> Tuple[List[Verdict], bool]:
        """
        Judges a single batch of up to 10 candidates.
        Re-asks once for missing IDs.
        Falls back to retrieval scores on persistent failure.
        """
        expected_ids: Set[int] = {c.movie_id for c in batch}
        cand_map: Dict[int, Candidate] = {c.movie_id for c in batch}
        fallback_used = False

        prompt = self._build_batch_prompt(profile, batch)

        try:
            res: JudgeBatchOutput = await self.llm.generate(prompt, JudgeBatchOutput)
            received_verdicts = {v.movie_id: v for v in res.verdicts if v.movie_id in expected_ids}

            # Check if any missing IDs
            missing_ids = expected_ids - set(received_verdicts.keys())
            if missing_ids:
                # Re-ask once for missing IDs
                missing_candidates = [c for c in batch if c.movie_id in missing_ids]
                reask_prompt = self._build_batch_prompt(profile, missing_candidates, is_reask=True)
                try:
                    reask_res: JudgeBatchOutput = await self.llm.generate(reask_prompt, JudgeBatchOutput)
                    for v in reask_res.verdicts:
                        if v.movie_id in missing_ids:
                            received_verdicts[v.movie_id] = v
                except Exception:
                    pass

            # If still missing any IDs, fill with deterministic fallback
            final_missing = expected_ids - set(received_verdicts.keys())
            if final_missing:
                fallback_used = True
                for mid in final_missing:
                    cand = next(c for c in batch if c.movie_id == mid)
                    received_verdicts[mid] = self._create_fallback_verdict(cand)

            # Return verdicts in the exact original batch order
            ordered_verdicts = [received_verdicts[c.movie_id] for c in batch]
            return ordered_verdicts, fallback_used

        except Exception:
            # Persistent failure: use full deterministic fallback for the batch
            fallback_used = True
            fallback_verdicts = self._deterministic_fallback_batch(batch)
            return fallback_verdicts, True

    def _build_batch_prompt(
        self,
        profile: Profile,
        candidates: List[Candidate],
        is_reask: bool = False
    ) -> str:
        intro = (
            "You are the Judging stage of CineMind.\n"
            "Evaluate each candidate movie against the user profile (likes, dislikes, constraints, mood).\n"
            "For EACH candidate movie_id, return match (boolean), fit (0.0 to 1.0), and a concise one-line reason.\n"
            "CRITICAL: If a candidate violates an explicit constraint (e.g. horror when forbidden), match MUST be false.\n\n"
        )
        if is_reask:
            intro += "NOTE: Some candidate IDs were missing in the previous response. Please evaluate ALL of the following movies:\n\n"

        p_info = (
            f"USER PROFILE:\n"
            f"- Summary: {profile.summary}\n"
            f"- Likes: {', '.join(profile.likes)}\n"
            f"- Dislikes: {', '.join(profile.dislikes)}\n"
            f"- Constraints: {', '.join(profile.constraints)}\n"
            f"- Mood: {profile.mood or 'None'}\n\n"
        )

        c_info = "CANDIDATES TO EVALUATE:\n"
        for c in candidates:
            c_info += (
                f"- ID: {c.movie_id} | Title: {c.title} ({c.year}) | Director: {c.director or 'Unknown'} | "
                f"Genres: {', '.join(c.genres or [])}\n"
                f"  Overview: {c.overview}\n"
            )

        c_info += "\nReturn a JSON object with 'verdicts': list of {movie_id, match, fit, reason}."
        return intro + p_info + c_info

    def _create_fallback_verdict(self, candidate: Candidate, is_match: bool = True) -> Verdict:
        fit = 0.85 if is_match else 0.35
        return Verdict(
            movie_id=candidate.movie_id,
            match=is_match,
            fit=fit,
            reason="Fallback verdict based on retrieval score relevance."
        )

    def _deterministic_fallback_batch(self, batch: List[Candidate]) -> List[Verdict]:
        # Sort by retrieval score descending
        sorted_batch = sorted(batch, key=lambda c: c.score, reverse=True)
        n_match = max(1, int(len(sorted_batch) * 0.4))
        match_ids = {c.movie_id for c in sorted_batch[:n_match]}

        verdicts: List[Verdict] = []
        for c in batch:
            is_m = c.movie_id in match_ids
            verdicts.append(self._create_fallback_verdict(c, is_match=is_m))
        return verdicts

    async def judge(
        self,
        profile: Profile,
        candidates: List[Candidate]
    ) -> Tuple[List[Verdict], bool]:
        if not candidates:
            return [], False

        batches = [candidates[i:i + self.batch_size] for i in range(0, len(candidates), self.batch_size)]
        all_verdicts: List[Verdict] = []
        any_fallback = False

        for b in batches:
            v_list, fb = await self.judge_batch(profile, b)
            all_verdicts.extend(v_list)
            if fb:
                any_fallback = True

        return all_verdicts, any_fallback
