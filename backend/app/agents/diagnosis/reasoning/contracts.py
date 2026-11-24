"""Provisional Manager DTOs; existing public Diagnosis fields retain their meaning."""

from typing import Literal

from pydantic import AwareDatetime, Field, field_validator, model_validator

from app.agents.diagnosis.code_rag.contracts import RetrievalRequest, RetrievedEvidence
from app.core.logging import redact
from app.db.types import utc_now
from app.schemas.common import WireModel
from app.schemas.domain import Diagnosis, Evidence, Identifier


class DiagnosisRequest(RetrievalRequest):
    """Mock Manager input bound to an existing incident and run, never a caller path."""

    incident_id: Identifier
    run_id: Identifier

    @model_validator(mode="after")
    def validate_query(self) -> "DiagnosisRequest":
        # Context may be populated from the incident; an empty caller query is valid here.
        from app.db.types import validate_token

        validate_token(self.repository_revision)
        return self

    @field_validator("error_type", "error_message", "stack_trace", "search_query")
    @classmethod
    def safe_text(cls, value: str) -> str:
        if any(ord(character) < 32 and character not in "\n\r\t" for character in value):
            raise ValueError("Incident text contains unsupported control characters")
        return redact(value)


class Hypothesis(WireModel):
    """An explicitly uncertain model interpretation supported by selected evidence IDs."""

    statement: str = Field(min_length=1, max_length=1000)
    evidence_ids: list[Identifier] = Field(min_length=1, max_length=5)
    uncertainty: str = Field(min_length=1, max_length=500)


class ReasoningDraft(WireModel):
    """Untrusted model output. No paths, line numbers, commands or patches are accepted."""

    hypotheses: list[Hypothesis] = Field(min_length=1, max_length=3)
    confidence_label: Literal["low", "medium", "high"]
    uncertainty: str = Field(min_length=1, max_length=1200)
    suggested_direction: str = Field(min_length=1, max_length=1200)
    needs_manual_review: bool


class ReasoningContext(WireModel):
    """Bounded sanitized observations and verified source passed as untrusted data."""

    error_type: str
    error_message: str
    stack_trace: str
    evidence: list[RetrievedEvidence]


class EvidenceFact(WireModel):
    """Service-generated source observation, distinct from an LLM hypothesis."""

    evidence_id: Identifier
    observation: str


class DiagnosisFailure(WireModel):
    code: str
    message: str


class DiagnosisResult(Diagnosis):
    """Internal result extends rather than replaces the existing frontend diagnosis DTO."""

    schema_version: Literal["1.0"] = "1.0"
    application_id: Identifier
    input_revision: str
    evidence: list[RetrievedEvidence]
    stage: Literal["diagnosis"] = "diagnosis"
    created_at: AwareDatetime = Field(default_factory=utc_now)
    outcome: Literal["diagnosed", "manual_review", "insufficient_evidence"]
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    facts: list[EvidenceFact] = Field(default_factory=list)
    provider: str
    used_test_fallback: bool = False
    error: DiagnosisFailure | None = None

    def to_public(self) -> Diagnosis:
        """Explicit compatible projection; never register a route or persist the result."""
        values = {key: getattr(self, key) for key in Diagnosis.model_fields if key != "evidence"}
        values["evidence"] = [
            Evidence.model_validate(item.model_dump(include=set(Evidence.model_fields)))
            for item in self.evidence
        ]
        return Diagnosis.model_validate(values)
