import pytest
from httpx import AsyncClient, ASGITransport
from src.cinemind.server import app

@pytest.mark.asyncio
async def test_frontend_static_serving():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Index
        res = await client.get("/")
        assert res.status_code == 200
        assert "CineMind" in res.text
        assert "scenarios-container" in res.text

        # Style CSS
        res_css = await client.get("/static/style.css")
        assert res_css.status_code == 200
        assert "--bg-canvas" in res_css.text

        # App JS
        res_js = await client.get("/static/app.js")
        assert res_js.status_code == 200
        assert "executeRecommendation" in res_js.text
