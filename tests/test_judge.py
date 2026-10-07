import pytest
from typing import List
from src.cinemind.agents.judge import JudgingAgent
from src.cinemind.llm import LLMClient
from src.cinemind.schemas import Profile, Candidate, Verdict, JudgeBatchOutput

class CustomStubLLM(LLMClient):
    def __init__(self, mode: str = "valid"):
        super().__init__(stub=True)
        self.mode = mode
        self.call_history: List[str] = []

    async def generate_raw(self, prompt: str, schema_dict=None, system=None) -> str:
        self.call_count += 1
        self.call_history.append(prompt)

        if self.mode == "malformed":
            return "{ corrupt_json: "

        if self.mode == "missing_ids":
            if self.call_count == 1:
                # Return verdict for only 1 of 3 candidates
                return '{"verdicts": [{"movie_id": 1, "match": true, "fit": 0.9, "reason": "Good match"}]}'
            else:
                # Re-ask returns the rest
                return '{"verdicts": [{"movie_id": 2, "match": false, "fit": 0.2, "reason": "No match"}, {"movie_id": 3, "match": true, "fit": 0.8, "reason": "Match"}]}'

        # Standard valid: return verdict for every candidate mentioned in prompt
        # Parse IDs from prompt
        import re
        ids = [int(m) for m in re.findall(r"ID:\s*(\d+)", prompt)]
        if not ids:
            ids = [1]
        verdicts = [{"movie_id": mid, "match": True, "fit": 0.9, "reason": "Matches preferences"} for mid in ids]
        import json
        return json.dumps({"verdicts": verdicts})

@pytest.mark.asyncio
async def test_judge_50_candidates_makes_5_calls():
    stub = CustomStubLLM(mode="valid")
    agent = JudgingAgent(llm=stub, batch_size=10)

    candidates = [
        Candidate(movie_id=i, title=f"Movie {i}", overview=f"Overview {i}", score=float(i))
        for i in range(1, 51)
    ]
    profile = Profile(likes=["Sci-Fi"], summary="Loves space")

    verdicts, fallback = await agent.judge(profile, candidates)

    assert len(verdicts) == 50
    assert stub.call_count == 5
    assert fallback is False

@pytest.mark.asyncio
async def test_judge_missing_ids_triggers_reask():
    stub = CustomStubLLM(mode="missing_ids")
    agent = JudgingAgent(llm=stub, batch_size=10)

    candidates = [
        Candidate(movie_id=1, title="Movie 1", overview="Overview 1", score=1.0),
        Candidate(movie_id=2, title="Movie 2", overview="Overview 2", score=2.0),
        Candidate(movie_id=3, title="Movie 3", overview="Overview 3", score=3.0)
    ]
    profile = Profile(likes=["Action"], summary="Wants thrill")

    verdicts, fallback = await agent.judge(profile, candidates)

    assert len(verdicts) == 3
    # 1 initial + 1 re-ask = 2 calls
    assert stub.call_count == 2
    assert {v.movie_id for v in verdicts} == {1, 2, 3}

@pytest.mark.asyncio
async def test_judge_persistent_failure_yields_fallback():
    stub = CustomStubLLM(mode="malformed")
    agent = JudgingAgent(llm=stub, batch_size=10)

    candidates = [
        Candidate(movie_id=1, title="Movie 1", overview="Overview 1", score=10.0),
        Candidate(movie_id=2, title="Movie 2", overview="Overview 2", score=5.0)
    ]
    profile = Profile(likes=["Drama"], summary="Deep drama")

    verdicts, fallback = await agent.judge(profile, candidates)

    assert len(verdicts) == 2
    assert fallback is True
    # Highest score movie should be matched in fallback top 40%
    v1 = next(v for v in verdicts if v.movie_id == 1)
    assert v1.match is True
