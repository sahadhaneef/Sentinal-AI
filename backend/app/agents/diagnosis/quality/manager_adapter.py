"""Pure wire mapping for manager-backend b74f09a; no registry or ORM integration."""

from dataclasses import asdict, is_dataclass
from typing import Any

from pydantic import Field

from app.agents.diagnosis.reasoning.contracts import DiagnosisRequest
from app.schemas.common import WireModel
from app.schemas.domain import Identifier

from .contracts import QualityResult


class ManagerExtra(WireModel):
    application_id: Identifier
    source_log: str = Field(default="", max_length=16000)
    error_type: str = Field(default="", max_length=200)
    error_message: str = Field(default="", max_length=2000)
    stack_trace_ref: Identifier | None = None


class ManagerInvocation(WireModel):
    incident_id: Identifier
    run_id: Identifier
    repository_revision: str
    extra: ManagerExtra


class ManagerOutcome(WireModel):
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    duration_ms: int = Field(ge=0)


def from_manager(value: Any) -> DiagnosisRequest:
    """Map the inspected dataclass/dict shape; never invent IDs, revisions or log refs."""
    payload = asdict(value) if is_dataclass(value) and not isinstance(value, type) else value
    wire = ManagerInvocation.model_validate(payload)
    if wire.repository_revision in {"HEAD", "main", "master", "latest"}:
        raise ValueError("Manager must supply the registered exact revision, not a moving alias")
    return DiagnosisRequest(
        incident_id=wire.incident_id,
        run_id=wire.run_id,
        application_id=wire.extra.application_id,
        repository_revision=wire.repository_revision,
        error_type=wire.extra.error_type,
        error_message=wire.extra.error_message,
        stack_trace=wire.extra.source_log,
        stack_trace_ref=wire.extra.stack_trace_ref,
    )


def to_manager(checked: QualityResult, duration_ms: int) -> ManagerOutcome:
    """Map normal review outcomes as status=manual_review; infrastructure failures stay errors."""
    result = checked.result
    if result.error and result.error.code in {
        "LLM_UNAVAILABLE",
        "TEST_FALLBACK_FAILED",
        "CONTEXT_UNAVAILABLE",
        "CONTEXT_SCOPE_MISMATCH",
        "INCIDENT_INPUT_CONFLICT",
        "LOG_SCOPE_MISMATCH",
    }:
        return ManagerOutcome(success=False, error=result.error.code, duration_ms=duration_ms)
    data = result.to_public().model_dump(mode="json")
    # Manager already carries these IDs in AgentInput and persists its own record.
    data.pop("incident_id")
    data.pop("run_id")
    return ManagerOutcome(success=True, data=data, duration_ms=duration_ms)
