"""Pure wire mapping for manager-backend b74f09a; no registry or ORM integration."""

from dataclasses import asdict, is_dataclass
from typing import Any

from pydantic import Field

from app.agents.diagnosis.reasoning.contracts import DiagnosisRequest
from app.db.types import Digest, validate_relative_key, validate_token
from app.schemas.common import WireModel
from app.schemas.domain import Identifier

from .contracts import CitationProvenance, QualityResult


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
    checked = validate_result(checked)
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


def validate_result(checked: QualityResult) -> QualityResult:
    """Check envelope consistency; source bytes remain the D3 resolver's responsibility."""
    checked = QualityResult.model_validate(checked.model_dump())
    result = checked.result
    validate_token(result.input_revision)
    if (result.application_id, result.input_revision) != (
        checked.provenance.application_id,
        checked.provenance.repository_revision,
    ):
        raise ValueError("Diagnosis provenance scope mismatch")
    citations = {item.evidence_id: item for item in checked.provenance.citations}
    if len(citations) != len(checked.provenance.citations):
        raise ValueError("Duplicate citation provenance")
    evidence_ids = {item.evidence_id for item in result.evidence}
    if len(evidence_ids) != len(result.evidence):
        raise ValueError("Duplicate result evidence")
    for item in result.evidence:
        validate_relative_key(item.file_path)
        for reference in (item.evidence_id, item.artifact_id, item.source_snapshot_ref):
            validate_token(reference)
        Digest().process_bind_param(item.content_hash, None)
        expected = CitationProvenance.model_validate(
            item.model_dump(include=set(CitationProvenance.model_fields))
        )
        if (
            item.application_id != result.application_id
            or item.repository_revision != result.input_revision
            or item.start_line < 1
            or item.end_line < item.start_line
            or item.evidence_id not in checked.assessment.verified_evidence_ids
            or citations.get(item.evidence_id) != expected
        ):
            raise ValueError("Diagnosis citation integrity mismatch")
    referenced = {key for hypothesis in result.hypotheses for key in hypothesis.evidence_ids}
    referenced.update(fact.evidence_id for fact in result.facts)
    if not referenced.issubset(evidence_ids):
        raise ValueError("Diagnosis references missing evidence")
    if result.status == "completed":
        if (
            result.outcome != "diagnosed"
            or not result.hypotheses
            or not result.evidence
            or result.error
            or checked.assessment.issues
            or result.used_test_fallback
        ):
            raise ValueError("Inconsistent completed diagnosis")
    elif result.outcome == "diagnosed":
        raise ValueError("Inconsistent review diagnosis")
    return checked
