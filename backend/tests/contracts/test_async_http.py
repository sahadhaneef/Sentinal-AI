import httpx
from fastapi.testclient import TestClient


async def test_async_httpx_transport_uses_same_live_app_contract(app):
    with TestClient(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.get("/api/v1/health")
            assert response.status_code == 200
            assert response.json()["meta"]["schema_version"] == "1.0"
            assert response.json()["data"]["status"] == "ok"
