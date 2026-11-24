"""Internal quality records without changing the shared Diagnosis or REST schemas."""

from pydantic import AwareDatetime, Field

from app.agents.diagnosis.reasoning.contracts import DiagnosisResult
from app.db.types import utc_now
from app.schemas.common import WireModel


class QualityIssue(WireModel):
    code: str
    action: str


class CitationProvenance(WireModel):
    evidence_id: str
    file_path: str
    start_line: int
    end_line: int
    content_hash: str
    source_snapshot_ref: str
    artifact_id: str
    retrieval_method: str
    rank: int
    semantic_score: float | None


class QualityAssessment(WireModel):
    issues: list[QualityIssue] = Field(default_factory=list)
    verified_evidence_ids: list[str] = Field(default_factory=list)


class RetrievalProvenance(WireModel):
    application_id: str
    repository_revision: str
    query_hash: str | None = None
    embedding_profile: str
    retrieval_status: str = "not_requested"
    retrieval_reason: str = "CONTEXT_NOT_VALIDATED"
    semantic_used: bool = False
    citations: list[CitationProvenance] = Field(default_factory=list)
    checked_at: AwareDatetime = Field(default_factory=utc_now)


class QualityResult(WireModel):
    """Record both retrieval provenance and the final reasoning/review outcome."""

    result: DiagnosisResult
    provenance: RetrievalProvenance
    assessment: QualityAssessment
    audit_event_id: str | None = None
