import pytest
from pydantic import BaseModel
from src.cinemind.llm import LLMClient, StageFailed
from src.cinemind.schemas import Profile

class SampleSchema(BaseModel):
    name: str
    score: int

@pytest.mark.asyncio
async def test_stub_llm_valid():
    client = LLMClient(stub=True, stub_mode="valid")
    profile = await client.generate("user query", Profile)
    assert isinstance(profile, Profile)
    assert len(profile.likes) > 0
    assert client.call_count == 1
    assert client.total_seconds >= 0

@pytest.mark.asyncio
async def test_stub_llm_malformed_raises_stage_failed():
    client = LLMClient(stub=True, stub_mode="malformed")
    with pytest.raises(StageFailed):
        await client.generate("test prompt", SampleSchema, max_retries=1)
    # 1 initial + 1 retry = 2 calls
    assert client.call_count == 2

@pytest.mark.asyncio
async def test_llm_ping():
    client = LLMClient(stub=True)
    assert await client.ping() is True

    # Real ping to localhost
    real_client = LLMClient(stub=False)
    assert await real_client.ping() is True
