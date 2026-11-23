from uuid import UUID

from fastapi.testclient import TestClient

from app import __version__
from app.schemas.common import Envelope, ErrorEnvelope
from app.schemas.health import Health


def test_health_matches_frozen_frontend_envelope(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    result = Envelope[Health].model_validate(response.json())
    assert result.data.status == "ok"
    assert result.data.version == __version__
    assert result.meta.schema_version == "1.0"
    assert str(UUID(result.meta.request_id)) == response.headers["x-request-id"]
    assert response.headers["cache-control"] == "no-store"


def test_request_ids_are_server_generated_per_request(client):
    first = client.get("/api/v1/health", headers={"X-Request-ID": "attacker-controlled"}).json()
    second = client.get("/api/v1/health").json()
    assert first["meta"]["request_id"] != "attacker-controlled"
    assert first["meta"]["request_id"] != second["meta"]["request_id"]


def test_openapi_advertises_phase_three_routes_and_explicit_guards(client: TestClient) -> None:
    result = client.get("/api/v1/openapi.json")
    assert result.status_code == 200
    schema = result.json()
    assert set(schema["paths"]) == {
        "/api/v1/health",
        "/api/v1/applications",
        "/api/v1/applications/{identity}",
        "/api/v1/applications/{identity}/metadata",
        "/api/v1/incidents",
        "/api/v1/incidents/{identity}",
        "/api/v1/incidents/{identity}/events",
        "/api/v1/incidents/{identity}/runs",
        "/api/v1/incidents/{identity}/diagnosis",
        "/api/v1/incidents/{identity}/patches",
        "/api/v1/patches/{identity}",
        "/api/v1/patches/{identity}/validation",
        "/api/v1/agents",
        "/api/v1/agents/{agent_type}",
        "/api/v1/dashboard/summary",
        "/api/v1/dashboard/overview",
        "/api/v1/settings",
        "/api/v1/reports",
        "/api/v1/reports/{identity}",
        "/api/v1/incidents/{identity}/reports",
        "/api/v1/incidents/{identity}/report",
        "/api/v1/incidents/{identity}/verification",
        "/api/v1/artifacts/{identity}",
        "/api/v1/incidents/{identity}/decision",
        "/api/v1/incidents/{identity}/apply",
        "/api/v1/applications/{identity}/monitoring/start",
        "/api/v1/applications/{identity}/monitoring/stop",
    }
    operation = schema["paths"]["/api/v1/health"]["get"]
    assert set(operation["responses"]) >= {"200", "404", "405", "422", "500"}
    assert client.get("/api/v1/docs").status_code == 200
    guard = schema["paths"]["/api/v1/incidents/{identity}/apply"]["post"]["responses"]["501"]
    assert guard["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorEnvelope")


def test_unimplemented_operations_are_not_fake_successes(client: TestClient) -> None:
    for method, path, status, code in [
        ("GET", "/api/v1/unknown-resource", 404, "NOT_FOUND"),
        ("POST", "/api/v1/incidents/inc_001/apply", 501, "NOT_IMPLEMENTED"),
        ("POST", "/api/v1/incidents/inc_001/decision", 501, "NOT_IMPLEMENTED"),
        ("POST", "/api/v1/auth/login", 404, "NOT_FOUND"),
    ]:
        result = client.request(method, path)
        assert result.status_code == status
        assert ErrorEnvelope.model_validate(result.json()).error.code == code
