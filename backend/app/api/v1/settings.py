"""Settings endpoints."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.security import get_current_actor
from ...db.models import Setting
from ...db.session import get_db
from ...schemas.common import ApiResponse, Meta, SafeBackendSettings

router = APIRouter(tags=["settings"])

_ALLOWED_KEYS = {"monitoring_interval_seconds", "max_candidate_revisions"}


async def _load_settings(db: AsyncSession) -> SafeBackendSettings:
    rows = (await db.scalars(select(Setting))).all()
    data = {r.key: json.loads(r.value_json) for r in rows if r.key in _ALLOWED_KEYS}
    return SafeBackendSettings(
        monitoring_interval_seconds=int(data.get("monitoring_interval_seconds", 5)),
        max_candidate_revisions=int(data.get("max_candidate_revisions", 2)),
    )


@router.get("/settings", response_model=ApiResponse[SafeBackendSettings])
async def get_settings_endpoint(request: Request, db: AsyncSession = Depends(get_db)):
    request_id = getattr(request.state, "request_id", "")
    settings = await _load_settings(db)
    return ApiResponse(data=settings, meta=Meta(request_id=request_id))


@router.patch("/settings", response_model=ApiResponse[SafeBackendSettings])
async def update_settings_endpoint(
    body: SafeBackendSettings,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    request_id = getattr(request.state, "request_id", "")
    get_current_actor(request)
    updates = {
        "monitoring_interval_seconds": body.monitoring_interval_seconds,
        "max_candidate_revisions": body.max_candidate_revisions,
    }
    for key, value in updates.items():
        row = await db.scalar(select(Setting).where(Setting.key == key))
        if row:
            row.value_json = json.dumps(value)
        else:
            db.add(Setting(key=key, value_json=json.dumps(value)))
    await db.commit()
    settings = await _load_settings(db)
    return ApiResponse(data=settings, meta=Meta(request_id=request_id))
