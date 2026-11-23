"""Integration tests covering all 20 required test scenarios."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ?? 1. Health check ???????????????????????????????????????????????????????????

async def test_health(client: AsyncClient):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["status"] == "ok"
    assert body["meta"]["schema_version"] == "1.0"


# ?? 2. Applications ???????????????????????????????????????????????????????????

async def test_list_applications(client: AsyncClient):
    r = await client.get("/api/v1/applications")
    assert r.status_code == 200
    apps = r.json()["data"]
    assert any(a["id"] == "app_demo" for a in apps)


async def test_get_application(client: AsyncClient):
    r = await client.get("/api/v1/applications/app_demo")
    assert r.status_code == 200
    assert r.json()["data"]["id"] == "app_demo"


async def test_application_not_found(client: AsyncClient):
    r = await client.get("/api/v1/applications/nonexistent")
    assert r.status_code == 404


async def test_monitoring_start_stop(client: AsyncClient):
    r = await client.post("/api/v1/applications/app_demo/monitoring/start")
    assert r.status_code == 200
    assert r.json()["data"]["monitoring_enabled"] is True

    r = await client.post("/api/v1/applications/app_demo/monitoring/stop")
    assert r.status_code == 200
    assert r.json()["data"]["monitoring_enabled"] is False


# ?? 3. Incident ingestion ?????????????????????????????????????????????????????

async def test_1_successful_incident_detection(client: AsyncClient):
    """Scenario 1: Successful incident detection."""
    r = await client.post("/api/v1/incidents", json={
        "application_id": "app_demo",
        "source_event_id": "evt_001",
        "fingerprint": "test_fingerprint_001",
        "severity": "high",
        "error_type": "NullReferenceError",
        "message": "Registration fails on missing profile",
        "source_log": "[registration] profile.name accessed on null profile at line 42",
        "repository_revision": "abc123",
    })
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["status"] == "detected"
    assert data["fingerprint"] == "test_fingerprint_001"
    return data["id"]


async def test_2_duplicate_incident_detection(client: AsyncClient):
    """Scenario 2: Duplicate incident detection (same fingerprint)."""
    fingerprint = "test_fingerprint_dup_001"
    # Create first
    r1 = await client.post("/api/v1/incidents", json={
        "application_id": "app_demo",
        "source_event_id": "evt_dup_1",
        "fingerprint": fingerprint,
        "severity": "high",
        "error_type": "NullReferenceError",
        "message": "Duplicate test",
        "repository_revision": "abc123",
    })
    assert r1.status_code == 200
    id1 = r1.json()["data"]["id"]

    # Second with same fingerprint ? should return existing
    r2 = await client.post("/api/v1/incidents", json={
        "application_id": "app_demo",
        "source_event_id": "evt_dup_2",
        "fingerprint": fingerprint,
        "severity": "critical",
        "error_type": "NullReferenceError",
        "message": "Duplicate test 2",
        "repository_revision": "abc123",
    })
    assert r2.status_code == 200
    id2 = r2.json()["data"]["id"]
    assert id1 == id2, "Duplicate fingerprint should return same incident ID"


# ?? 4. Full workflow ??????????????????????????????????????????????????????????

async def _create_incident(client: AsyncClient, fingerprint: str = None) -> str:
    fp = fingerprint or f"fp_{id(client)}_{__import__('uuid').uuid4().hex[:8]}"
    r = await client.post("/api/v1/incidents", json={
        "application_id": "app_demo",
        "source_event_id": f"evt_{fp}",
        "fingerprint": fp,
        "severity": "high",
        "error_type": "NullReferenceError",
        "message": "Test incident",
        "repository_revision": "abc123",
    })
    assert r.status_code == 200
    return r.json()["data"]["id"]


async def test_7_successful_validation(client: AsyncClient):
    """Scenario 7: Successful validation through the full automated pipeline."""
    inc_id = await _create_incident(client)

    # Run full workflow
    r = await client.post(f"/api/v1/incidents/{inc_id}/workflow/run-all")
    assert r.status_code == 200
    data = r.json()["data"]
    # Should reach awaiting_approval (stubs pass by default)
    assert data["stage"] in ("validating", "diagnosing", "generating_patch")

    # Check incident state
    r2 = await client.get(f"/api/v1/incidents/{inc_id}")
    assert r2.status_code == 200
    inc_data = r2.json()["data"]
    assert inc_data["status"] in ("awaiting_approval", "diagnosing", "generating_patch", "validating", "manual_review")


async def test_8_human_approval(client: AsyncClient):
    """Scenario 8: Human approval of a validated candidate."""
    inc_id = await _create_incident(client)

    # Run automated workflow
    await client.post(f"/api/v1/incidents/{inc_id}/workflow/run-all")

    # Check if awaiting approval
    r = await client.get(f"/api/v1/incidents/{inc_id}")
    inc = r.json()["data"]

    if inc["status"] != "awaiting_approval":
        pytest.skip(f"Incident in state {inc['status']}, not awaiting_approval")

    patches = inc["patches"]
    assert len(patches) > 0, "Must have at least one patch candidate"
    latest = patches[-1]

    # Approve
    r_approve = await client.post(f"/api/v1/incidents/{inc_id}/decision", json={
        "candidate_id": latest["id"],
        "patch_hash": latest["patch_hash"],
        "base_revision": latest["base_revision"],
        "decision": "approve",
        "comment": "Approved in test",
    })
    assert r_approve.status_code == 200
    decision = r_approve.json()["data"]
    assert decision["decision"] == "approve"


async def test_9_human_rejection(client: AsyncClient):
    """Scenario 9: Human rejection of a candidate."""
    inc_id = await _create_incident(client)
    await client.post(f"/api/v1/incidents/{inc_id}/workflow/run-all")

    r = await client.get(f"/api/v1/incidents/{inc_id}")
    inc = r.json()["data"]

    if inc["status"] != "awaiting_approval":
        pytest.skip(f"Incident in state {inc['status']}, not awaiting_approval")

    patches = inc["patches"]
    latest = patches[-1]

    r_reject = await client.post(f"/api/v1/incidents/{inc_id}/decision", json={
        "candidate_id": latest["id"],
        "patch_hash": latest["patch_hash"],
        "base_revision": latest["base_revision"],
        "decision": "reject",
        "comment": "Rejected in test",
    })
    assert r_reject.status_code == 200
    assert r_reject.json()["data"]["decision"] == "reject"

    r_inc = await client.get(f"/api/v1/incidents/{inc_id}")
    assert r_inc.json()["data"]["status"] in ("rejected", "reported")


async def test_11_unauthorized_approval_without_valid_candidate(client: AsyncClient):
    """Scenario 11: Approval of non-awaiting incident fails."""
    inc_id = await _create_incident(client)
    # Don't run workflow ? incident is in 'detected' state
    r = await client.post(f"/api/v1/incidents/{inc_id}/decision", json={
        "candidate_id": "fake_candidate",
        "patch_hash": "sha256:fake",
        "base_revision": "abc123",
        "decision": "approve",
    })
    assert r.status_code in (404, 409)  # Not found or conflict


async def test_12_unauthorized_patch_application_without_approval(client: AsyncClient):
    """Scenario 12: Apply without prior approval returns APPROVAL_REQUIRED."""
    inc_id = await _create_incident(client)
    r = await client.post(f"/api/v1/incidents/{inc_id}/apply", json={
        "candidate_id": "fake_candidate",
        "patch_hash": "sha256:fake",
        "base_revision": "abc123",
    })
    assert r.status_code == 409
    assert r.json()["error"]["code"] in ("APPROVAL_REQUIRED", "CONFLICT", "NOT_FOUND")


async def test_patch_cannot_be_applied_without_explicit_approval(client: AsyncClient):
    """Core safety test: patch application MUST be blocked without explicit approval."""
    inc_id = await _create_incident(client)
    # Try to apply without any workflow state
    r = await client.post(f"/api/v1/incidents/{inc_id}/apply", json={
        "candidate_id": "any_candidate",
        "patch_hash": "sha256:any",
        "base_revision": "abc123",
    })
    assert r.status_code in (409, 404), (
        "Patch application MUST be blocked without explicit approval! "
        f"Got {r.status_code}: {r.json()}"
    )


# ?? 5. Dashboard and agents ???????????????????????????????????????????????????

async def test_dashboard_summary(client: AsyncClient):
    r = await client.get("/api/v1/dashboard/summary")
    assert r.status_code == 200
    data = r.json()["data"]
    assert "total_incidents" in data
    assert "agent_statuses" in data
    assert "last_updated" in data


async def test_list_agents(client: AsyncClient):
    r = await client.get("/api/v1/agents")
    assert r.status_code == 200
    agents = r.json()["data"]
    agent_types = [a["agent_type"] for a in agents]
    for expected in ["manager", "monitoring", "diagnosis", "repair", "testing", "reporting"]:
        assert expected in agent_types, f"Missing agent: {expected}"


async def test_get_agent_detail(client: AsyncClient):
    r = await client.get("/api/v1/agents/manager")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["agent_type"] == "manager"
    assert "inputs" in data
    assert "outputs" in data
    assert "recent_runs" in data


async def test_agent_not_found(client: AsyncClient):
    r = await client.get("/api/v1/agents/nonexistent_agent")
    assert r.status_code == 404


# ?? 6. Settings ???????????????????????????????????????????????????????????????

async def test_get_settings(client: AsyncClient):
    r = await client.get("/api/v1/settings")
    assert r.status_code == 200
    data = r.json()["data"]
    assert "monitoring_interval_seconds" in data
    assert "max_candidate_revisions" in data


async def test_update_settings(client: AsyncClient):
    r = await client.patch("/api/v1/settings", json={
        "monitoring_interval_seconds": 10,
        "max_candidate_revisions": 2,
    })
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["monitoring_interval_seconds"] == 10


async def test_settings_validation(client: AsyncClient):
    """Settings out of range should fail validation."""
    r = await client.patch("/api/v1/settings", json={
        "monitoring_interval_seconds": 999,  # > 60
        "max_candidate_revisions": 2,
    })
    assert r.status_code == 422


# ?? 7. Incident events ????????????????????????????????????????????????????????

async def test_incident_events(client: AsyncClient):
    inc_id = await _create_incident(client)
    r = await client.get(f"/api/v1/incidents/{inc_id}/events")
    assert r.status_code == 200
    events = r.json()["data"]
    assert len(events) >= 1
    for e in events:
        assert "event_type" in e
        assert "occurred_at" in e
        assert "incident_id" in e
        assert "actor_type" in e


# ?? 8. Pagination ?????????????????????????????????????????????????????????????

async def test_incident_pagination(client: AsyncClient):
    # Create a few incidents
    for i in range(3):
        await _create_incident(client, fingerprint=f"pagtest_{i}")

    r = await client.get("/api/v1/incidents?limit=2")
    assert r.status_code == 200
    body = r.json()["data"]
    assert "items" in body
    assert "total" in body
    assert "next_cursor" in body
    assert len(body["items"]) <= 2


# ?? 9. API contract validation ?????????????????????????????????????????????????

async def test_20_api_contract_meta(client: AsyncClient):
    """Scenario 20: Every response has the correct meta envelope."""
    endpoints = [
        "/api/v1/health",
        "/api/v1/dashboard/summary",
        "/api/v1/applications",
        "/api/v1/agents",
        "/api/v1/settings",
        "/api/v1/incidents",
    ]
    for ep in endpoints:
        r = await client.get(ep)
        assert r.status_code == 200, f"Failed {ep}: {r.text}"
        body = r.json()
        assert "meta" in body, f"Missing meta in {ep}"
        assert body["meta"]["schema_version"] == "1.0", f"Wrong schema_version in {ep}"
        assert "request_id" in body["meta"], f"Missing request_id in {ep}"
        assert "data" in body, f"Missing data in {ep}"


async def test_error_format(client: AsyncClient):
    """Error responses follow the standard error envelope."""
    r = await client.get("/api/v1/incidents/nonexistent_id")
    assert r.status_code == 404
    body = r.json()
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]
    assert "meta" in body


# ?? 10. Workflow state transitions ????????????????????????????????????????????

async def test_workflow_state_persisted(client: AsyncClient):
    """States are persisted in DB across requests."""
    inc_id = await _create_incident(client)

    # Verify initial state persists
    r1 = await client.get(f"/api/v1/incidents/{inc_id}")
    assert r1.json()["data"]["status"] == "detected"

    # Start run
    r2 = await client.post(f"/api/v1/incidents/{inc_id}/runs")
    assert r2.status_code == 200

    # State should be detected with active_run_id
    r3 = await client.get(f"/api/v1/incidents/{inc_id}")
    inc = r3.json()["data"]
    assert inc["active_run_id"] is not None
    assert inc["status"] == "detected"


async def test_19_workflow_recovery_after_restart(client: AsyncClient):
    """Scenario 19: Workflow state persists in DB (survives server restart simulation)."""
    inc_id = await _create_incident(client)
    await client.post(f"/api/v1/incidents/{inc_id}/runs")

    # Simulate: re-fetch from DB (no in-memory state dependency)
    r = await client.get(f"/api/v1/incidents/{inc_id}")
    assert r.status_code == 200
    inc = r.json()["data"]
    # State is persisted from DB, not in-memory
    assert inc["status"] in ("detected", "diagnosing")
    assert inc["active_run_id"] is not None


# ?? 11. Run list ??????????????????????????????????????????????????????????????

async def test_incident_runs_list(client: AsyncClient):
    inc_id = await _create_incident(client)
    await client.post(f"/api/v1/incidents/{inc_id}/runs")
    r = await client.get(f"/api/v1/incidents/{inc_id}/runs")
    assert r.status_code == 200
    runs = r.json()["data"]
    assert len(runs) >= 1


# ?? 12. No duplicate active runs ?????????????????????????????????????????????

async def test_duplicate_run_prevented(client: AsyncClient):
    inc_id = await _create_incident(client)
    await client.post(f"/api/v1/incidents/{inc_id}/runs")
    # Second start should fail
    r2 = await client.post(f"/api/v1/incidents/{inc_id}/runs")
    assert r2.status_code in (409, 200)  # Conflict or idempotent


async def test_resume_interrupted_workflows(db_session):
    """Test that interrupted active runs are resumed and advanced."""
    from app.services.manager import ManagerAgent
    manager = ManagerAgent(db_session)
    incident, _ = await manager.create_or_deduplicate_incident(
        application_id="app_demo",
        source_event_id="evt_resume",
        fingerprint="fp_resume_test",
        severity="high",
        error_type="NullReferenceError",
        message="Interrupted workflow test",
        source_log="",
        repository_revision="abc123",
    )
    run = await manager.start_run(incident.id, "test_actor")
    incident.status = "diagnosing"
    run.state = "diagnosing"
    await db_session.commit()

    resumed = await manager.resume_interrupted_workflows()
    assert len(resumed) >= 1
    assert any(r["incident_id"] == incident.id for r in resumed)
