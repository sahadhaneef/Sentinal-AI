"""Approval decision and patch application endpoints."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.security import check_idempotency, record_idempotency, require_actor, verify_csrf
from ...db.session import get_db
from ...schemas.common import (
    ApiResponse,
    ApplyRequest,
    ApprovalRequest,
    AttemptOut,
    DecisionOut,
    Meta,
)
from ...services.manager import ManagerAgent

router = APIRouter(tags=["approvals"])


@router.post("/incidents/{incident_id}/decision", response_model=ApiResponse[DecisionOut])
async def make_decision(
    incident_id: str,
    body: ApprovalRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Human approval gate ? approve or reject a patch candidate."""
    verify_csrf(request)
    actor = require_actor(request)
    request_id = getattr(request.state, "request_id", "")
    idempotency_key = request.headers.get("Idempotency-Key")

    if idempotency_key:
        cached = await check_idempotency(db, idempotency_key)
        if cached:
            return JSONResponse(status_code=cached.response_status, content=json.loads(cached.response_json))

    manager = ManagerAgent(db)
    result = await manager.approve_candidate(
        incident_id=incident_id,
        candidate_id=body.candidate_id,
        patch_hash=body.patch_hash,
        base_revision=body.base_revision,
        decision=body.decision,
        actor_id=actor,
        comment=body.comment,
    )
    decision_out = DecisionOut(
        id=result["id"],
        incident_id=incident_id,
        candidate_id=result["candidate_id"],
        patch_hash=result["patch_hash"],
        base_revision=result["base_revision"],
        decision=result["decision"],
        actor_id=result["actor_id"],
        comment=result.get("comment"),
        decided_at=result["decided_at"],
    )
    resp = ApiResponse(data=decision_out, meta=Meta(request_id=request_id))

    if idempotency_key:
        await record_idempotency(
            db, idempotency_key, request.url.path, actor, 200, json.dumps(resp.model_dump(mode="json"))
        )

    return resp


@router.post("/incidents/{incident_id}/apply", response_model=ApiResponse[AttemptOut])
async def apply_patch(
    incident_id: str,
    body: ApplyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Controlled application of an approved patch to the demo workspace only."""
    verify_csrf(request)
    actor = require_actor(request)
    request_id = getattr(request.state, "request_id", "")
    idempotency_key = request.headers.get("Idempotency-Key")

    if idempotency_key:
        cached = await check_idempotency(db, idempotency_key)
        if cached:
            return JSONResponse(status_code=cached.response_status, content=json.loads(cached.response_json))

    manager = ManagerAgent(db)
    result = await manager.apply_approved_patch(
        incident_id=incident_id,
        candidate_id=body.candidate_id,
        patch_hash=body.patch_hash,
        base_revision=body.base_revision,
    )

    from sqlalchemy import select

    from ...db.models import ApplicationAttempt
    attempt = await db.scalar(select(ApplicationAttempt).where(ApplicationAttempt.id == result["attempt_id"]))

    attempt_out = AttemptOut(
        id=attempt.id,
        candidate_id=attempt.candidate_id,
        snapshot_ref=attempt.snapshot_ref,
        before_revision=attempt.before_revision,
        after_revision=attempt.after_revision,
        status=attempt.status,
        applied_at=attempt.applied_at,
        restore_status=attempt.restore_status,
    )
    resp = ApiResponse(data=attempt_out, meta=Meta(request_id=request_id))

    if idempotency_key:
        await record_idempotency(
            db, idempotency_key, request.url.path, actor, 200, json.dumps(resp.model_dump(mode="json"))
        )

    return resp
