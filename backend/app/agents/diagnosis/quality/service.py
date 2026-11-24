"""Per-invocation D3 gateway around D2 with preserved retrieval/outcome provenance."""

from sqlalchemy import Engine

from app.agents.diagnosis.code_rag.contracts import RetrievalRequest, RetrievalResult
from app.agents.diagnosis.code_rag.hashing import canonical, digest
from app.agents.diagnosis.code_rag.service import CodeRag
from app.agents.diagnosis.reasoning.config import DiagnosisSettings
from app.agents.diagnosis.reasoning.contracts import (
    DiagnosisFailure,
    DiagnosisRequest,
    DiagnosisResult,
)
from app.agents.diagnosis.reasoning.providers import ReasoningProvider
from app.agents.diagnosis.reasoning.service import UNCERTAINTY, DiagnosisService
from app.core.config import Settings
from app.db.types import utc_now

from .contracts import CitationProvenance, QualityAssessment, QualityResult, RetrievalProvenance
from .evidence import EvidencePolicy


class QualityRag(CodeRag):
    """Fully initialized D1-compatible gateway; each invocation has its own provenance."""

    def __init__(self, base: CodeRag, policy: EvidencePolicy, request: DiagnosisRequest) -> None:
        super().__init__(base.catalog.engine, base.catalog.settings, base.rag, base.provider)
        self.base, self.policy = base, policy
        self.assessment = QualityAssessment()
        self.provenance = RetrievalProvenance(
            application_id=request.application_id,
            repository_revision=request.repository_revision,
            embedding_profile=base.provider.profile,
        )

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        result = self.base.retrieve(request)
        self.provenance.query_hash = digest(canonical(request.model_dump()))
        self.provenance.retrieval_status = result.status
        self.provenance.retrieval_reason = result.reason
        self.provenance.semantic_used = result.semantic_used
        self.assessment = self.policy.assess(request, result, self.evidence)
        self.provenance.checked_at = utc_now()
        verified = set(self.assessment.verified_evidence_ids)
        self.provenance.citations = [
            CitationProvenance.model_validate(
                item.model_dump(include=set(CitationProvenance.model_fields))
            )
            for item in result.evidence
            if item.evidence_id in verified
        ]
        if self.assessment.issues:
            return RetrievalResult(
                application_id=request.application_id,
                repository_revision=request.repository_revision,
                status="unavailable",
                reason=self.assessment.issues[0].code,
                semantic_used=False,
                evidence=[],
            )
        return result


class QualityDiagnosisService:
    """No automatic writes; provenance can be explicitly recorded using OutcomeRecorder."""

    def __init__(
        self,
        engine: Engine,
        settings: Settings,
        rag: CodeRag,
        config: DiagnosisSettings | None = None,
        provider: ReasoningProvider | None = None,
        policy: EvidencePolicy | None = None,
    ) -> None:
        self.engine, self.settings, self.rag = engine, settings, rag
        self.config, self.provider = config, provider
        self.policy = policy or EvidencePolicy()

    def diagnose(self, request: DiagnosisRequest) -> QualityResult:
        request = DiagnosisRequest.model_validate(request.model_dump())
        gateway = QualityRag(self.rag, self.policy, request)
        service = DiagnosisService(
            self.engine, self.settings, gateway, config=self.config, provider=self.provider
        )
        result = service.diagnose(request)
        gateway.assessment.issues.extend(self.policy.check_findings(result))
        if gateway.assessment.issues:
            issue = gateway.assessment.issues[0]
            result = DiagnosisResult.model_validate(
                result.model_dump()
                | {
                    "status": "manual_review",
                    "outcome": "insufficient_evidence",
                    "hypothesis": "The available evidence does not support a specific cause.",
                    "hypotheses": [],
                    "confidence_label": "low",
                    "uncertainty": UNCERTAINTY + " " + issue.action,
                    "suggested_direction": issue.action,
                    "error": DiagnosisFailure(code=issue.code, message=issue.action).model_dump(),
                }
            )
        return QualityResult(
            result=result, provenance=gateway.provenance, assessment=gateway.assessment
        )
