"""Tests for reviewer authentication, CSRF enforcement, Idempotency-Key, and approval safety gates."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_session_token
from app.db.session import get_db
from app.main import app

pytestmark = pytest.mark.asyncio


async def test_auth_login_logout(client: AsyncClient):
    """Reviewer can login and logout cleanly."""
    res = await client.post("/api/v1/auth/login", json={"username": "alice_reviewer", "role": "reviewer"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["actor_id"] == "alice_reviewer"
    assert data["authenticated"] is True

    # Check /me
    me_res = await client.get("/api/v1/auth/me")
    assert me_res.status_code == 200

    # Logout
    logout_res = await client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 200


async def test_csrf_mismatch_rejected(db_session: AsyncSession):
    """CSRF mismatch raises 403 Forbidden."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={"csrf_token": "valid_token", "sentinel_session": create_session_token("reviewer1")},
        headers={"X-CSRF-Token": "wrong_token"},
    ) as ac:
        r = await ac.post("/api/v1/incidents/inc_fake/decision", json={
            "candidate_id": "c1",
            "patch_hash": "sha256:fake",
            "base_revision": "abc123",
            "decision": "approve",
        })
        assert r.status_code == 403

    app.dependency_overrides.clear()


async def test_idempotency_key_replay(client: AsyncClient, db_session: AsyncSession):
    """Sending the same Idempotency-Key returns cached response without duplicate operations."""
    # Create incident
    inc_res = await client.post("/api/v1/incidents", json={
        "application_id": "app_demo",
        "source_event_id": "evt_idem",
        "fingerprint": "fp_idem_01",
        "severity": "high",
        "error_type": "NullReferenceError",
        "message": "Idempotency test",
        "repository_revision": "abc123",
    })
    inc_id = inc_res.json()["data"]["id"]

    # Run workflow
    await client.post(f"/api/v1/incidents/{inc_id}/workflow/run-all")

    # Fetch candidate
    inc_detail = (await client.get(f"/api/v1/incidents/{inc_id}")).json()["data"]
    candidate = inc_detail["patches"][-1]

    idem_key = "test-idem-key-999"
    headers = {"Idempotency-Key": idem_key, "X-CSRF-Token": "test_csrf"}

    # First decision call
    r1 = await client.post(
        f"/api/v1/incidents/{inc_id}/decision",
        json={
            "candidate_id": candidate["id"],
            "patch_hash": candidate["patch_hash"],
            "base_revision": candidate["base_revision"],
            "decision": "approve",
            "comment": "Initial approval",
        },
        headers=headers,
    )
    assert r1.status_code == 200
    decision1 = r1.json()["data"]

    # Second decision call with identical Idempotency-Key
    r2 = await client.post(
        f"/api/v1/incidents/{inc_id}/decision",
        json={
            "candidate_id": candidate["id"],
            "patch_hash": candidate["patch_hash"],
            "base_revision": candidate["base_revision"],
            "decision": "approve",
            "comment": "Initial approval",
        },
        headers=headers,
    )
    assert r2.status_code == 200
    decision2 = r2.json()["data"]
    # Should return exact cached decision
    assert decision1["id"] == decision2["id"]
    assert decision1["decided_at"] == decision2["decided_at"]


async def test_stale_candidate_rejected(client: AsyncClient):
    """Applying with wrong patch hash or wrong base revision raises 409 CANDIDATE_STALE."""
    # Create incident
    inc_res = await client.post("/api/v1/incidents", json={
        "application_id": "app_demo",
        "source_event_id": "evt_stale",
        "fingerprint": "fp_stale_01",
        "severity": "high",
        "error_type": "NullReferenceError",
        "message": "Stale candidate test",
        "repository_revision": "abc123",
    })
    inc_id = inc_res.json()["data"]["id"]
    await client.post(f"/api/v1/incidents/{inc_id}/workflow/run-all")

    r = await client.post(f"/api/v1/incidents/{inc_id}/decision", json={
        "candidate_id": "patch_fake",
        "patch_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
        "base_revision": "abc123",
        "decision": "approve",
    })
    assert r.status_code in (404, 409)


async def test_cannot_apply_before_approval(client: AsyncClient):
    """Direct patch application before approval is blocked with 409 APPROVAL_REQUIRED."""
    inc_res = await client.post("/api/v1/incidents", json={
        "application_id": "app_demo",
        "source_event_id": "evt_unapproved",
        "fingerprint": "fp_unapproved_01",
        "severity": "high",
        "error_type": "NullReferenceError",
        "message": "Unapproved test",
        "repository_revision": "abc123",
    })
    inc_id = inc_res.json()["data"]["id"]
    await client.post(f"/api/v1/incidents/{inc_id}/workflow/run-all")

    inc_detail = (await client.get(f"/api/v1/incidents/{inc_id}")).json()["data"]
    candidate = inc_detail["patches"][-1]

    # Attempt to apply directly without calling /decision
    r = await client.post(f"/api/v1/incidents/{inc_id}/apply", json={
        "candidate_id": candidate["id"],
        "patch_hash": candidate["patch_hash"],
        "base_revision": candidate["base_revision"],
    })
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "APPROVAL_REQUIRED"
