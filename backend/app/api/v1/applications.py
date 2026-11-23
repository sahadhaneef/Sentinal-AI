"""Applications endpoints."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import NotFoundError
from ...core.security import get_current_actor
from ...db.models import Application
from ...db.session import get_db
from ...schemas.common import ApiResponse, ApplicationOut, Meta

router = APIRouter(tags=["applications"])


def _to_app_out(app: Application) -> ApplicationOut:
    return ApplicationOut(
        id=app.id,
        name=app.name,
        description=app.description,
        workspace_key=app.workspace_key,
        repository_revision=app.repository_revision,
        monitoring_enabled=app.monitoring_enabled,
        status=app.status,
        supported_errors=json.loads(app.supported_errors),
    )


@router.get("/applications", response_model=ApiResponse[list[ApplicationOut]])
async def list_applications(request: Request, db: AsyncSession = Depends(get_db)):
    request_id = getattr(request.state, "request_id", "")
    apps = (await db.scalars(select(Application))).all()
    return ApiResponse(data=[_to_app_out(a) for a in apps], meta=Meta(request_id=request_id))


@router.get("/applications/{app_id}", response_model=ApiResponse[ApplicationOut])
async def get_application(app_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    request_id = getattr(request.state, "request_id", "")
    app = await db.scalar(select(Application).where(Application.id == app_id))
    if not app:
        raise NotFoundError("Application")
    return ApiResponse(data=_to_app_out(app), meta=Meta(request_id=request_id))


@router.post("/applications/{app_id}/monitoring/start", response_model=ApiResponse[ApplicationOut])
async def start_monitoring(
    app_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    request_id = getattr(request.state, "request_id", "")
    get_current_actor(request)
    app = await db.scalar(select(Application).where(Application.id == app_id))
    if not app:
        raise NotFoundError("Application")
    app.monitoring_enabled = True
    app.status = "degraded"
    await db.commit()
    await db.refresh(app)
    return ApiResponse(data=_to_app_out(app), meta=Meta(request_id=request_id))


@router.post("/applications/{app_id}/monitoring/stop", response_model=ApiResponse[ApplicationOut])
async def stop_monitoring(
    app_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    request_id = getattr(request.state, "request_id", "")
    get_current_actor(request)
    app = await db.scalar(select(Application).where(Application.id == app_id))
    if not app:
        raise NotFoundError("Application")
    app.monitoring_enabled = False
    app.status = "healthy"
    await db.commit()
    await db.refresh(app)
    return ApiResponse(data=_to_app_out(app), meta=Meta(request_id=request_id))
