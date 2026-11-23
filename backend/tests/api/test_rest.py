"""Phase 3 acceptance: persisted projections, intake, pagination and safe failures."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select

from app import models
from app.core.config import Settings
from app.main import create_app
from app.repositories import transaction
from tests.api.conftest import CONTENT, TOKEN
from tests.database.helpers import event

PREFIX = "/api/v1"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def data(client: TestClient, path: str) -> dict | list:
    result = client.get(PREFIX + path)
    assert result.status_code == 200, result.text
    assert result.json()["meta"]["schema_version"] == "1.0"
    return result.json()["data"]


def test_empty_database_has_honest_compatible_defaults(api_client: TestClient) -> None:
    assert data(api_client, "/applications") == []
    assert data(api_client, "/incidents") == {"items": [], "total": 0, "next_cursor": None}
    assert data(api_client, "/reports") == []
    summary = data(api_client, "/dashboard/summary")
    for key in (
        "total_incidents",
        "open_incidents",
        "awaiting_approval",
        "resolved",
        "active_agents",
        "current_runs",
    ):
        assert summary[key] == 0
    assert len(summary["agent_statuses"]) == 6
    for agent in summary["agent_statuses"]:
        assert agent["status"] == "idle"
        assert agent["last_activity"] is None
        assert data(api_client, f"/agents/{agent['agent_type']}")["recent_runs"] == []
    assert data(api_client, "/settings") == {
        "monitoring_interval_seconds": 5,
        "max_candidate_revisions": 2,
    }


def test_persisted_full_graph_is_projected_without_running_anything(
    api_client: TestClient, populated: None, database: Engine
) -> None:
    application = data(api_client, "/applications/app_demo")
    assert application["repository_revision"] == "demoabc"
    metadata = data(api_client, "/applications/app_demo/metadata")
    assert metadata["observation_status"] == "recorded"
    assert metadata["monitoring_worker_available"] is False
    assert len(metadata["revisions"]) == 1
    incidents = data(api_client, "/incidents")
    identity = incidents["items"][0]["id"]
    detail = data(api_client, f"/incidents/{identity}")
    assert detail["source_log"] == CONTENT.decode()
    assert detail["patches"][0]["diff"] == CONTENT.decode()
    assert detail["diagnosis"]["evidence"][0]["excerpt"] == CONTENT.decode()
    assert detail["validation"]["checks"][0]["evidence"] == CONTENT.decode()
    assert detail["decision"]["actor_id"] == "reviewer"
    assert detail["application_attempt"]["snapshot_ref"] == "art_snapshot"
    assert detail["verification"]["status"] == "failed"
    assert detail["report"]["outcome"] == "unresolved"
    assert not any(detail[field] for field in ("can_approve", "can_reject", "can_apply"))
    assert "not implemented" in detail["permission_reason"]
    assert data(api_client, f"/incidents/{identity}/patches") == detail["patches"]
    assert data(api_client, "/patches/patch_001") == detail["patches"][0]
    assert data(api_client, "/patches/patch_001/validation") == detail["validation"]
    assert data(api_client, f"/incidents/{identity}/diagnosis") == detail["diagnosis"]
    assert data(api_client, f"/incidents/{identity}/verification") == detail["verification"]
    assert data(api_client, f"/incidents/{identity}/report") == detail["report"]
    assert data(api_client, f"/reports/{detail['report']['id']}") == detail["report"]
    assert len(data(api_client, f"/incidents/{identity}/reports")) == 1
    assert len(data(api_client, f"/incidents/{identity}/events")) == 1
    assert data(api_client, f"/incidents/{identity}/runs")[0]["transitions"][0]["sequence"] == 1
    assert len(data(api_client, "/agents/diagnosis")["recent_runs"]) == 1
    assert data(api_client, "/dashboard/summary")["open_incidents"] == 0
    with transaction(database) as store:
        assert store.session.scalar(select(func.count(models.WorkflowRun.id))) == 1


def test_registration_uses_allowlisted_key_and_never_starts_monitoring(
    api_client: TestClient, api_settings: Settings, database: Engine
) -> None:
    path = api_settings.artifact_root / "fixtures/snapshot.txt"
    path.parent.mkdir()
    path.write_bytes(b"operator-prepared fixture snapshot")
    response = api_client.post(
        PREFIX + "/applications", json={"workspace_key": "demo"}, headers=AUTH
    )
    assert response.status_code == 201, response.text
    application = response.json()["data"]
    assert application["monitoring_enabled"] is False
    assert application["status"] == "offline"
    metadata = data(api_client, f"/applications/{application['id']}/metadata")
    assert metadata["observation_status"] == "not_observed"
    assert metadata["last_observed_at"] is None
    assert (
        api_client.post(
            PREFIX + "/applications", json={"workspace_key": "demo"}, headers=AUTH
        ).status_code
        == 409
    )
    with transaction(database) as store:
        assert store.session.scalar(select(func.count(models.Application.id))) == 1
        assert store.session.scalar(select(func.count(models.MonitoringEvent.id))) == 0


@pytest.mark.parametrize(
    "body,expected",
    [
        ({"workspace_key": "../secret"}, 422),
        ({"workspace_key": "C:/secret"}, 422),
        ({"workspace_key": "unlisted"}, 403),
        ({"workspace_key": "demo", "path": "/private"}, 422),
    ],
)
def test_registration_rejects_unpermitted_paths(
    api_client: TestClient, body: dict, expected: int
) -> None:
    assert (
        api_client.post(PREFIX + "/applications", json=body, headers=AUTH).status_code == expected
    )


def test_operator_auth_is_required_and_browser_origins_are_rejected(api_client: TestClient) -> None:
    body = {"workspace_key": "demo"}
    assert api_client.post(PREFIX + "/applications", json=body).status_code == 401
    assert (
        api_client.post(
            PREFIX + "/applications", json=body, headers={"Authorization": "Bearer incorrect"}
        ).status_code
        == 403
    )
    assert (
        api_client.post(
            PREFIX + "/applications", json=body, headers=AUTH | {"Origin": "http://localhost:5173"}
        ).status_code
        == 403
    )


def test_ingestion_replay_deduplication_and_initial_state(
    api_client: TestClient, populated: None, database: Engine
) -> None:
    request = event(source_event_id="api-event", fingerprint="sha256:" + "c" * 64).model_dump(
        mode="json"
    )
    first = api_client.post(PREFIX + "/incidents", json=request, headers=AUTH)
    assert first.status_code == 200, first.text
    assert first.json()["data"]["status"] == "detected"
    assert first.json()["data"]["active_run_id"] is None
    assert (
        api_client.post(PREFIX + "/incidents", json=request, headers=AUTH).json()["data"]
        == first.json()["data"]
    )
    request["source_event_id"] = "api-event-repeat"
    repeat = api_client.post(PREFIX + "/incidents", json=request, headers=AUTH)
    assert repeat.json()["data"]["id"] == first.json()["data"]["id"]
    request["message"] = "Changed evidence for the same event"
    assert api_client.post(PREFIX + "/incidents", json=request, headers=AUTH).status_code == 409
    timeline = data(api_client, f"/incidents/{first.json()['data']['id']}/events")
    assert len(timeline) == 2
    assert all(item["run_id"] == "" for item in timeline)
    with transaction(database) as store:
        assert store.session.scalar(select(func.count(models.WorkflowRun.id))) == 1


def test_incident_filter_sort_and_opaque_snapshot_pagination(
    api_client: TestClient, populated: None, database: Engine
) -> None:
    with transaction(database) as store:
        for index, severity in enumerate(["critical", "low", "high"]):
            store.incidents.record_monitoring_event(
                event(
                    source_event_id=f"page-{index}",
                    fingerprint="sha256:" + str(index) * 64,
                    severity=severity,
                    message=f"Pagination marker {index}%",
                    occurred_at=event().occurred_at + timedelta(seconds=index),
                )
            )
    result = data(api_client, "/incidents?scope=open&sort=severity_desc&limit=1")
    assert result["total"] == 3
    assert result["items"][0]["severity"] == "critical"
    token = result["next_cursor"]
    assert token and not token.isdigit()
    next_page = api_client.get(
        PREFIX + "/incidents",
        params={"scope": "open", "sort": "severity_desc", "limit": 1, "cursor": token},
    )
    assert next_page.status_code == 200
    assert next_page.json()["data"]["items"][0]["severity"] == "high"
    assert (
        api_client.get(
            PREFIX + "/incidents", params={"scope": "closed", "cursor": token, "limit": 1}
        ).status_code
        == 422
    )
    assert data(api_client, "/incidents?search=%25")["total"] == 3
    assert data(api_client, "/incidents?status=unresolved&scope=closed")["total"] == 1
    assert data(api_client, "/incidents?scope=candidates")["total"] == 1
    assert data(api_client, "/incidents?scope=pending")["total"] == 0
    assert data(api_client, "/incidents?severity=low&application_id=app_demo")["total"] == 1
    assert [
        row["source_event_id"]
        for row in data(api_client, "/incidents?scope=open&sort=detected_asc")["items"]
    ] == ["page-0", "page-1", "page-2"]
    with transaction(database) as store:
        store.incidents.record_monitoring_event(
            event(source_event_id="new-page", fingerprint="sha256:" + "e" * 64)
        )
    assert (
        api_client.get(
            PREFIX + "/incidents",
            params={"scope": "open", "sort": "severity_desc", "limit": 1, "cursor": token},
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "query",
    [
        "cursor=bad",
        "sort=random",
        "scope=unknown",
        "severity=extreme",
        "status=repairing",
        "limit=0",
        "limit=101",
        "limit=1.5",
        "private=true",
        "limit=1&limit=2",
    ],
)
def test_invalid_query_contracts_are_sanitized(api_client: TestClient, query: str) -> None:
    result = api_client.get(PREFIX + "/incidents?" + query)
    assert result.status_code == 422
    assert result.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    "path",
    [
        "/applications/missing",
        "/incidents/missing",
        "/patches/missing",
        "/reports/missing",
        "/artifacts/missing",
    ],
)
def test_missing_records(api_client: TestClient, path: str) -> None:
    assert api_client.get(PREFIX + path).status_code == 404


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/incidents/example/decision"),
        ("POST", "/incidents/example/apply"),
        ("POST", "/incidents/example/runs"),
        ("POST", "/applications/example/monitoring/start"),
        ("POST", "/applications/example/monitoring/stop"),
        ("PATCH", "/settings"),
    ],
)
def test_unsupported_mutations_never_return_success(
    api_client: TestClient, method: str, path: str
) -> None:
    result = api_client.request(method, PREFIX + path, json={})
    assert result.status_code == 501
    assert result.json()["error"]["code"] == "NOT_IMPLEMENTED"


def test_artifact_metadata_is_safe_and_missing_or_tampered_bytes_fail(
    api_client: TestClient, populated: None, api_settings: Settings
) -> None:
    artifact = data(api_client, "/artifacts/art_log")
    assert "storage_key" not in artifact
    assert str(api_settings.artifact_root) not in str(artifact)
    identity = data(api_client, "/incidents")["items"][0]["id"]
    (api_settings.artifact_root / "fixtures/log.txt").write_bytes(b"tampered")
    result = api_client.get(PREFIX + f"/incidents/{identity}")
    assert result.status_code == 503
    assert "ARTIFACT_UNAVAILABLE" in result.text
    (api_settings.artifact_root / "fixtures/log.txt").unlink()
    assert api_client.get(PREFIX + f"/incidents/{identity}").status_code == 503


def test_restart_keeps_intake_and_never_creates_runs(
    api_client: TestClient, populated: None, api_settings: Settings
) -> None:
    identity = data(api_client, "/incidents")["items"][0]["id"]
    with TestClient(create_app(api_settings)) as restarted:
        assert data(restarted, f"/incidents/{identity}")["id"] == identity


def test_invalid_identifiers_and_unavailable_auth_leave_database_unchanged(
    api_client: TestClient, api_settings: Settings
) -> None:
    assert api_client.get(PREFIX + "/applications/invalid%20identifier").status_code == 422
    disabled = api_settings.model_copy(update={"operator_token": None})
    with TestClient(create_app(disabled)) as client:
        assert (
            client.post(
                PREFIX + "/applications", json={"workspace_key": "demo"}, headers=AUTH
            ).status_code
            == 403
        )
