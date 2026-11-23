"""Dashboard summary endpoint."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ...agents.registry import get_registry
from ...db.session import get_db
from ...schemas.common import AgentSummaryOut, ApiResponse, DashboardSummaryOut, Meta

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/summary", response_model=ApiResponse[DashboardSummaryOut])
async def get_dashboard_summary(request: Request, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func, select

    from ...db.models import Incident

    request_id = getattr(request.state, "request_id", "")
    registry = get_registry()

    # Aggregate counts from DB
    total = await db.scalar(select(func.count(Incident.id))) or 0
    closed = ["resolved", "rejected", "unresolved", "reported"]
    open_count = await db.scalar(
        select(func.count(Incident.id)).where(~Incident.status.in_(closed))
    ) or 0
    awaiting = await db.scalar(
        select(func.count(Incident.id)).where(Incident.status == "awaiting_approval")
    ) or 0
    resolved_count = await db.scalar(
        select(func.count(Incident.id)).where(Incident.status == "resolved")
    ) or 0
    active_states = ["applying", "verifying", "validating", "diagnosing", "generating_patch"]
    current_runs = await db.scalar(
        select(func.count(Incident.id)).where(Incident.status.in_(active_states))
    ) or 0

    # Agent statuses from registry
    agent_statuses = [
        AgentSummaryOut(**a.to_summary()) for a in registry.all()
    ]
    active_agents = sum(1 for a in agent_statuses if a.status == "running")

    summary = DashboardSummaryOut(
        total_incidents=total,
        open_incidents=open_count,
        awaiting_approval=awaiting,
        resolved=resolved_count,
        active_agents=active_agents,
        current_runs=current_runs,
        agent_statuses=agent_statuses,
        last_updated=datetime.now(UTC),
    )
    return ApiResponse(data=summary, meta=Meta(request_id=request_id))
