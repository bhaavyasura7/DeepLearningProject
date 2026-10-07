import pytest
from pathlib import Path
from src.cinemind.agents.understand import UnderstandingAgent, EmptyInput
from src.cinemind.cache import ProfileCache
from src.cinemind.llm import LLMClient
from src.cinemind.schemas import Rated, Profile

@pytest.mark.asyncio
async def test_understand_agent_stub(tmp_path: Path):
    cache = ProfileCache(cache_path=tmp_path / "cache.json")
    llm = LLMClient(stub=True, stub_mode="valid")
    agent = UnderstandingAgent(llm=llm, cache=cache)

    # 1. Valid output parses to Profile
    profile = await agent.understand(query="fun sci-fi like Inception")
    assert isinstance(profile, Profile)
    assert len(profile.likes) > 0
    assert profile.summary
    assert llm.call_count == 1

    # 2. Second identical call is a cache hit with zero additional model calls
    profile2 = await agent.understand(query="fun sci-fi like Inception")
    assert profile2.summary == profile.summary
    assert llm.call_count == 1  # Still 1! Cache hit

@pytest.mark.asyncio
async def test_understand_empty_input_raises_empty_input():
    agent = UnderstandingAgent()
    with pytest.raises(EmptyInput):
        await agent.understand(history=[], query="")

    with pytest.raises(EmptyInput):
        await agent.understand(history=None, query=None)
