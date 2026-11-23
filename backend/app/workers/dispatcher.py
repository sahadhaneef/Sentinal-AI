"""Durable workflow dispatcher.

Coordinates background execution of workflow stages with DB persistence.
Does not rely exclusively on in-memory state or ephemeral tasks.
"""
from __future__ import annotations

import asyncio
from typing import Any

from ..core.logging import get_logger
from ..db.session import get_session_factory
from ..services.manager import ManagerAgent

logger = get_logger(__name__)


class WorkflowDispatcher:
    """Dispatches and tracks durable asynchronous workflow executions."""

    def __init__(self) -> None:
        self._active_tasks: dict[str, asyncio.Task] = {}

    def dispatch_automated_run(self, incident_id: str, actor_id: str = "dispatcher") -> asyncio.Task:
        """Enqueue and launch a persistent automated workflow run in the background."""
        task = asyncio.create_task(
            self._run_pipeline(incident_id, actor_id),
            name=f"pipeline_{incident_id}",
        )
        self._active_tasks[incident_id] = task
        task.add_done_callback(lambda _: self._active_tasks.pop(incident_id, None))
        return task

    async def _run_pipeline(self, incident_id: str, actor_id: str) -> dict[str, Any]:
        """Execute automated stages (diagnosis -> repair -> test) with DB persistence."""
        factory = get_session_factory()
        async with factory() as session:
            manager = ManagerAgent(session)

            # Start run record in DB
            await manager.start_run(incident_id, actor_id=actor_id)

            # Stage 1: Diagnosis
            diag_res = await manager.run_diagnosis_stage(incident_id)
            if diag_res.get("status") in ("manual_review", "error"):
                logger.info("Workflow paused for manual review during diagnosis", extra={"incident_id": incident_id})
                return diag_res

            # Stage 2: Repair
            repair_res = await manager.run_repair_stage(incident_id)
            if repair_res.get("status") in ("unresolved", "manual_review", "error"):
                logger.info("Workflow halted during repair", extra={"incident_id": incident_id})
                return repair_res

            # Stage 3: Testing
            test_res = await manager.run_testing_stage(incident_id)
            logger.info("Workflow automated pipeline completed", extra={"incident_id": incident_id, "test_status": test_res.get("status")})
            return test_res


_dispatcher: WorkflowDispatcher | None = None


def get_dispatcher() -> WorkflowDispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = WorkflowDispatcher()
    return _dispatcher
