"""API-level safety checks on recorded evidence, empty views and honest outcomes."""

import hashlib
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app import models
from app.core.config import Settings
from app.repositories import transaction
from app.services import cursors
from tests.api.test_rest import AUTH, PREFIX, data
from tests.database.helpers import event


def test_unrelated_missing_artifacts_do_not_break_summary_or_verification_reads(
    api_client: TestClient,
    populated: None,
    api_settings: Settings,
    database: Engine,
) -> None:
    identity = data(api_client, "/incidents")["items"][0]["id"]
    with transaction(database) as store:
        execution = next(
            row
            for row in store.records(models.AgentExecution).list()
            if row.agent_type == "diagnosis"
        )
        store.records(models.AgentExecution).update(
            execution.id, status="error", error_artifact_id="art_log"
        )
    (api_settings.artifact_root / "fixtures/log.txt").unlink()
    agents = data(api_client, "/agents")
    assert (
        next(agent for agent in agents if agent["agent_type"] == "diagnosis")["status"] == "error"
    )
    assert data(api_client, "/dashboard/summary")["total_incidents"] == 1
    assert data(api_client, f"/incidents/{identity}/verification")["status"] == "failed"
    assert api_client.get(PREFIX + "/agents/diagnosis").status_code == 503
    assert api_client.get(PREFIX + f"/incidents/{identity}").status_code == 503


def test_tampered_expired_and_restart_cursors_are_rejected(
    api_client: TestClient,
    populated: None,
    database: Engine,
    api_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.main import create_app

    with transaction(database) as store:
        store.incidents.record_monitoring_event(
            event(source_event_id="cursor-second", fingerprint="sha256:" + "b" * 64)
        )
    monkeypatch.setattr(cursors, "time", SimpleNamespace(time=lambda: 1000))
    token = data(api_client, "/incidents?limit=1")["next_cursor"]
    assert token
    bad = ("x" if token[0] != "x" else "y") + token[1:]
    assert (
        api_client.get(PREFIX + "/incidents", params={"limit": 1, "cursor": bad}).status_code == 422
    )
    with TestClient(create_app(api_settings)) as restarted:
        assert (
            restarted.get(PREFIX + "/incidents", params={"limit": 1, "cursor": token}).status_code
            == 422
        )
    monkeypatch.setattr(cursors, "time", SimpleNamespace(time=lambda: 2000))
    assert (
        api_client.get(PREFIX + "/incidents", params={"limit": 1, "cursor": token}).status_code
        == 422
    )


def test_overview_and_recorded_agent_activity_are_database_backed(
    api_client: TestClient,
    populated: None,
    database: Engine,
) -> None:
    with transaction(database) as store:
        execution = next(
            row
            for row in store.records(models.AgentExecution).list()
            if row.agent_type == "diagnosis"
        )
        store.records(models.AgentExecution).update(execution.id, status="running")
    overview = data(api_client, "/dashboard/overview")
    assert overview["registered_applications"] == 1
    assert overview["incidents_by_severity"] == {"low": 0, "medium": 0, "high": 1, "critical": 0}
    assert overview["summary"]["active_agents"] == 1
    assert len(overview["recent_activity"]) == 1
    assert overview["recent_outcomes"][0]["outcome"] == "unresolved"


def test_pending_queue_and_new_candidate_do_not_inherit_validation(
    api_client: TestClient,
    populated: None,
    database: Engine,
) -> None:
    identity = data(api_client, "/incidents")["items"][0]["id"]
    with transaction(database) as store:
        original = store.patches.get("patch_001")
        store.patches.add(
            models.PatchCandidate(
                id="patch_002",
                incident_id=identity,
                run_id=original.run_id,
                application_id=original.application_id,
                version=2,
                base_revision=original.base_revision,
                patch_hash=original.patch_hash,
                changed_files=original.changed_files,
                rationale="Second explicit metadata fixture",
                diff_artifact_id=original.diff_artifact_id,
                supersedes_candidate_id=original.id,
            )
        )
        store.incidents.update(identity, status="awaiting_approval")
    pending = data(api_client, "/incidents?scope=pending")
    assert pending["total"] == 1
    assert data(api_client, "/dashboard/summary")["awaiting_approval"] == 1
    detail = data(api_client, f"/incidents/{identity}")
    assert [row["version"] for row in detail["patches"]] == [1, 2]
    assert detail["validation"] is None
    assert detail["decision"] is None
    assert api_client.get(PREFIX + "/patches/patch_002/validation").status_code == 404


def test_missing_results_and_unsupported_failure_intake_are_honest(
    api_client: TestClient,
    populated: None,
) -> None:
    payload = event(
        source_event_id="unsupported-api",
        error_type="NewError",
        classification="unsupported",
        fingerprint="sha256:" + "d" * 64,
    ).model_dump(mode="json")
    response = api_client.post(PREFIX + "/incidents", json=payload, headers=AUTH)
    assert response.status_code == 200
    incident_id = response.json()["data"]["id"]
    assert response.json()["data"]["status"] == "manual_review"
    assert data(api_client, f"/incidents/{incident_id}/patches") == []
    for suffix in ("report", "diagnosis", "verification"):
        assert api_client.get(PREFIX + f"/incidents/{incident_id}/{suffix}").status_code == 404
    payload["classification"] = "supported"
    payload["source_event_id"] = "unsupported-as-supported"
    assert api_client.post(PREFIX + "/incidents", json=payload, headers=AUTH).status_code == 422
    payload["actor_id"] = "spoofed-reviewer"
    assert api_client.post(PREFIX + "/incidents", json=payload, headers=AUTH).status_code == 422


def test_reports_and_dashboard_refuse_unsupported_recovery_claims(
    api_client: TestClient,
    populated: None,
    database: Engine,
) -> None:
    identity = data(api_client, "/incidents")["items"][0]["id"]
    with transaction(database) as store:
        report = store.records(models.IncidentReport).list()[0]
        report.outcome = "resolved"
        store.incidents.update(identity, status="resolved")
    for path in (f"/incidents/{identity}", f"/incidents/{identity}/report", "/dashboard/summary"):
        result = api_client.get(PREFIX + path)
        assert result.status_code == 409
        assert result.json()["error"]["code"] == "EVIDENCE_INCOMPLETE"


def test_redaction_and_unicode_literal_search_are_preserved(
    api_client: TestClient,
    populated: None,
) -> None:
    payload = event(
        source_event_id="safe-message",
        fingerprint="sha256:" + "c" * 64,
        message="CAFÉ failure token=private-credential",
    ).model_dump(mode="json")
    result = api_client.post(PREFIX + "/incidents", json=payload, headers=AUTH)
    assert result.status_code == 200
    assert "private-credential" not in result.text
    listing = api_client.get(PREFIX + "/incidents", params={"search": "café"}).json()["data"]
    assert listing["total"] == 1
    joined = api_client.get(PREFIX + "/incidents", params={"search": "KeyError CAFÉ"}).json()[
        "data"
    ]
    assert joined["total"] == 1


def test_artifact_projection_refuses_secret_text_and_excessive_size(
    api_client: TestClient,
    populated: None,
    api_settings: Settings,
    database: Engine,
) -> None:
    identity = data(api_client, "/incidents")["items"][0]["id"]
    secret = b"token=private-credential"
    (api_settings.artifact_root / "fixtures/log.txt").write_bytes(secret)
    with transaction(database) as store:
        artifact = store.records(models.Artifact).get("art_log")
        artifact.sha256 = "sha256:" + hashlib.sha256(secret).hexdigest()
        artifact.size_bytes = len(secret)
    result = api_client.get(PREFIX + f"/incidents/{identity}")
    assert result.status_code == 403
    assert "private-credential" not in result.text
    (api_settings.artifact_root / "fixtures/log.txt").write_bytes(
        b"x" * (api_settings.artifact_max_bytes + 1)
    )
    assert api_client.get(PREFIX + f"/incidents/{identity}").status_code == 503
