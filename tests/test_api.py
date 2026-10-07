import pytest
from httpx import AsyncClient, ASGITransport
from src.cinemind.server import app
from src.cinemind.llm import default_llm

@pytest.mark.asyncio
async def test_health_check_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert "model_ready" in data
        assert "catalog_size" in data
        assert data["catalog_size"] > 0
        assert "graph_ready" in data

@pytest.mark.asyncio
async def test_scenarios_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/scenarios")
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 6

@pytest.mark.asyncio
async def test_recommend_empty_input_returns_400():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/recommend", json={"mode": "query", "query": "", "history": []})
        assert res.status_code == 400
        assert "Empty request" in res.json()["detail"]

@pytest.mark.asyncio
async def test_recommend_replay_unknown_scenario_returns_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/recommend", json={
            "mode": "query",
            "query": "something",
            "replay": True,
            "scenario_id": "nonexistent_scenario_123"
        })
        assert res.status_code == 404

@pytest.mark.asyncio
async def test_recommend_replay_valid_scenario_returns_200():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/recommend", json={
            "mode": "query",
            "query": "sci fi",
            "replay": True,
            "scenario_id": "nolan_scifi",
            "retrieval": "hybrid"
        })
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]

@pytest.mark.asyncio
async def test_compare_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/compare/nolan_scifi")
        assert res.status_code == 200
        data = res.json()
        assert "vector" in data
        assert "hybrid" in data
        assert data["vector"] is not None
        assert data["hybrid"] is not None

@pytest.mark.asyncio
async def test_results_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/results")
        assert res.status_code == 200
        data = res.json()
        assert "metrics" in data
        assert "vector" in data["metrics"]
        assert "hybrid" in data["metrics"]
