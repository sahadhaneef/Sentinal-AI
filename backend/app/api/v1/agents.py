"""Agents endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...agents.registry import AgentType, get_registry
from ...core.errors import NotFoundError
from ...db.models import AgentExecution, IncidentRun
from ...db.session import get_db
from ...schemas.common import AgentDetailOut, AgentSummaryOut, ApiResponse, ExecutionOut, Meta

router = APIRouter(tags=["agents"])

_AGENT_META = {
    "manager": {
        "name": "Manager Agent",
        "owner": "Delvin",
        "responsibility": "Coordinates the workflow and keeps every handoff accountable.",
        "inputs": ["Incident events, typed agent handoffs"],
        "outputs": ["Stage dispatch, approval gates, audit events"],
    },
    "monitoring": {
        "name": "Monitoring Agent",
        "owner": "Neha",
        "responsibility": "Spots supported failures in the designated sample application.",
        "inputs": ["Allowlisted sample logs"],
        "outputs": ["Sanitized, deduplicated incident events"],
    },
    "diagnosis": {
        "name": "Diagnosis Agent",
        "owner": "Sahad",
        "responsibility": "Connects errors to revision-bound code evidence with Code RAG.",
        "inputs": ["Error context, exact repository revision"],
        "outputs": ["Cited hypothesis, uncertainty, suggested direction"],
    },
    "repair": {
        "name": "Repair Agent",
        "owner": "Yadhulakshmi",
        "responsibility": "Proposes focused, reviewable patches with a clear rationale.",
        "inputs": ["Diagnosis evidence, source revision"],
        "outputs": ["Immutable patch candidate, diff, hash"],
    },
    "testing": {
        "name": "Testing Agent",
        "owner": "Sravan",
        "responsibility": "Validates candidates in isolation before human review.",
        "inputs": ["Exact patch candidate, reproduction fixture"],
        "outputs": ["Check results, test evidence, verification"],
    },
    "reporting": {
        "name": "Reporting Agent",
        "owner": "Neha",
        "responsibility": "Turns the incident journey into a clear, evidence-led report.",
        "inputs": ["Persisted decisions and verification results"],
        "outputs": ["Outcome report, limitations, audit summary"],
    },
}


async def _get_recent_runs(db: AsyncSession, agent_type: str, limit: int = 5) -> list[ExecutionOut]:
    execs = (await db.scalars(
        select(AgentExecution)
        .where(AgentExecution.agent_type == agent_type)
        .order_by(AgentExecution.started_at.desc())
        .limit(limit)
    )).all()

    result = []
    for ex in execs:
        run = await db.scalar(select(IncidentRun).where(IncidentRun.id == ex.run_id))
        incident_id = run.incident_id if run else "unknown"
        result.append(ExecutionOut(
            schema_version="1.0",
            incident_id=incident_id,
            run_id=ex.run_id,
            stage=agent_type,
            agent_type=agent_type,
            status=ex.status,
            created_at=ex.started_at,
            input_revision=ex.input_revision,
            error=ex.error_json,
        ))
    return result


@router.get("/agents", response_model=ApiResponse[list[AgentSummaryOut]])
async def list_agents(request: Request, db: AsyncSession = Depends(get_db)):
    request_id = getattr(request.state, "request_id", "")
    registry = get_registry()

    # Manager agent (not in registry but we include its info)
    agents = []

    # Manager first
    manager_meta = _AGENT_META["manager"]
    manager_execs = await _get_recent_runs(db, "manager", 1)
    agents.append(AgentSummaryOut(
        agent_type="manager",
        name=manager_meta["name"],
        status="idle",
        responsibility=manager_meta["responsibility"],
        owner=manager_meta["owner"],
        current_task=None,
        last_activity=manager_execs[0].created_at.isoformat() if manager_execs else None,
    ))

    # Other agents from registry
    for agent in registry.all():
        await _get_recent_runs(db, agent.agent_type.value, 1)
        agents.append(AgentSummaryOut(
            agent_type=agent.agent_type.value,
            name=agent.name,
            status=agent.status.value,
            responsibility=agent.responsibility,
            owner=agent.owner,
            current_task=agent.current_task,
            last_activity=agent.last_activity,
        ))

    return ApiResponse(data=agents, meta=Meta(request_id=request_id))


@router.get("/agents/{agent_type}", response_model=ApiResponse[AgentDetailOut])
async def get_agent(agent_type: str, request: Request, db: AsyncSession = Depends(get_db)):
    request_id = getattr(request.state, "request_id", "")
    if agent_type not in _AGENT_META:
        raise NotFoundError("Agent")

    meta = _AGENT_META[agent_type]
    recent_runs = await _get_recent_runs(db, agent_type)

    if agent_type == "manager":
        return ApiResponse(
            data=AgentDetailOut(
                agent_type="manager",
                name=meta["name"],
                status="idle",
                responsibility=meta["responsibility"],
                owner=meta["owner"],
                current_task=None,
                last_activity=recent_runs[0].created_at.isoformat() if recent_runs else None,
                inputs=meta["inputs"],
                outputs=meta["outputs"],
                recent_runs=recent_runs,
            ),
            meta=Meta(request_id=request_id),
        )

    registry = get_registry()
    try:
        agent = registry.get(AgentType(agent_type))
    except (ValueError, KeyError):
        raise NotFoundError("Agent")

    return ApiResponse(
        data=AgentDetailOut(
            agent_type=agent.agent_type.value,
            name=agent.name,
            status=agent.status.value,
            responsibility=agent.responsibility,
            owner=agent.owner,
            current_task=agent.current_task,
            last_activity=agent.last_activity,
            inputs=agent.inputs,
            outputs=agent.outputs,
            recent_runs=recent_runs,
        ),
        meta=Meta(request_id=request_id),
    )
