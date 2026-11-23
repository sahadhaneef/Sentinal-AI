"""API v1 router ? aggregates all endpoint modules."""
from __future__ import annotations

from fastapi import APIRouter

from .agents import router as agents_router
from .applications import router as applications_router
from .approvals import router as approvals_router
from .artifacts import router as artifacts_router
from .auth import router as auth_router
from .dashboard import router as dashboard_router
from .health import router as health_router
from .incidents import router as incidents_router
from .patches import router as patches_router
from .settings import router as settings_router

router = APIRouter()

router.include_router(health_router)
router.include_router(auth_router)
router.include_router(dashboard_router)
router.include_router(applications_router)
router.include_router(incidents_router)
router.include_router(agents_router)
router.include_router(patches_router)
router.include_router(approvals_router)
router.include_router(artifacts_router)
router.include_router(settings_router)
