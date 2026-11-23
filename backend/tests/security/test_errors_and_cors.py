from fastapi import Query
from fastapi.testclient import TestClient

from app.core.errors import ApiError


def test_method_error_keeps_allow_and_metadata(client):
    result = client.post("/api/v1/health")
    assert result.status_code == 405
    assert "GET" in result.headers["allow"]
    assert result.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert result.json()["meta"]["request_id"] == result.headers["x-request-id"]


def test_validation_does_not_echo_raw_input(app):
    @app.get("/test-only-validation")
    def validate(count: int = Query(ge=1)):
        return {"count": count}

    with TestClient(app) as client:
        result = client.get("/test-only-validation", params={"count": "private-credential"})
    assert result.status_code == 422
    assert result.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "private-credential" not in result.text
    assert result.json()["error"]["details"]["fields"][0]["location"] == ["query", "count"]


def test_internal_failure_is_generic_and_has_cors_and_correlation(app):
    @app.get("/test-only-failure")
    def fail():
        raise RuntimeError("password=database-secret /private/workspace")

    with TestClient(app, raise_server_exceptions=False) as client:
        result = client.get("/test-only-failure", headers={"Origin": "http://localhost:5173"})
    assert result.status_code == 500
    assert result.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "database-secret" not in result.text
    assert "/private" not in result.text
    assert "RuntimeError" not in result.text
    assert result.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert result.json()["meta"]["request_id"] == result.headers["x-request-id"]


def test_typed_error_preserves_non_success_status(app):
    @app.get("/test-only-conflict")
    def conflict():
        raise ApiError(409, "CANDIDATE_STALE", "Review the current candidate.")

    with TestClient(app) as client:
        result = client.get("/test-only-conflict")
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "CANDIDATE_STALE"


def test_credentialed_preflight_allows_exact_origin_and_expected_headers(client):
    result = client.options(
        "/api/v1/incidents/example/decision",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,idempotency-key,x-csrf-token",
        },
    )
    assert result.status_code == 200
    assert result.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert result.headers["access-control-allow-credentials"] == "true"
    assert "origin" in result.headers["vary"].lower()


def test_unlisted_origin_is_never_granted_credentialed_cors(client):
    headers = {"Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST"}
    result = client.options("/api/v1/health", headers=headers)
    assert result.status_code == 400
    assert "access-control-allow-origin" not in result.headers
    result = client.get("/api/v1/health", headers={"Origin": "http://localhost:9999"})
    assert "access-control-allow-origin" not in result.headers


def test_no_foundation_route_sets_fake_sessions_or_secrets(client):
    response = client.get("/api/v1/health")
    assert "set-cookie" not in response.headers
    assert "api_key" not in response.text
    assert response.headers["x-content-type-options"] == "nosniff"
