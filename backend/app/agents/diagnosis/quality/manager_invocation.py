"""Unregistered async test seam; selects no worker, persistence or retry policy."""

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Any

from app.agents.diagnosis.reasoning.contracts import DiagnosisRequest

from .contracts import QualityResult
from .manager_adapter import ManagerOutcome, from_manager, to_manager


async def invoke_manager_request(
    value: Any,
    diagnose: Callable[[DiagnosisRequest], Awaitable[QualityResult]],
) -> ManagerOutcome:
    """Translate one cooperative invocation without hiding cancellation or retrying.

    The current synchronous service must not be passed directly. Production worker
    and session ownership require agreement before a real async callback is wired.
    """
    if not inspect.iscoroutinefunction(diagnose):
        raise TypeError("A cooperative async Diagnosis callback is required")
    started = monotonic()
    try:
        request = from_manager(value)
    except (ValueError, TypeError):
        raise ValueError("Invalid Manager diagnosis request") from None
    try:
        checked = await diagnose(request.model_copy(deep=True))
    except Exception:
        raise RuntimeError("Diagnosis invocation failed") from None
    task = asyncio.current_task()
    if task is not None and task.cancelling():
        raise asyncio.CancelledError
    try:
        result = checked.result
        if (result.incident_id, result.run_id, result.application_id, result.input_revision) != (
            request.incident_id,
            request.run_id,
            request.application_id,
            request.repository_revision,
        ):
            raise ValueError("Diagnosis response scope mismatch")
        return to_manager(checked, int((monotonic() - started) * 1000))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Invalid Diagnosis response") from None
