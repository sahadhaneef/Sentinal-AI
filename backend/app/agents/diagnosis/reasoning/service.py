"""Evidence-bound Diagnosis reasoning with explicit uncertainty and no workflow writes."""

import logging

from pydantic import ValidationError
from sqlalchemy import Engine

from app.agents.diagnosis.code_rag.contracts import RetrievalRequest, RetrievedEvidence
from app.agents.diagnosis.code_rag.errors import RagError
from app.agents.diagnosis.code_rag.service import CodeRag
from app.core.config import Settings
from app.core.errors import ApiError
from app.core.logging import redact
from app.repositories.errors import PersistenceError

from .config import DiagnosisSettings
from .contracts import (
    DiagnosisFailure,
    DiagnosisRequest,
    DiagnosisResult,
    EvidenceFact,
    ReasoningContext,
    ReasoningDraft,
)
from .providers import DisabledProvider, OllamaProvider, ReasoningProvider
from .repository import ContextRejected, DiagnosisContextRepository

LOGGER = logging.getLogger("sentinel.diagnosis")
UNCERTAINTY = (
    "Source-supported hypotheses only; execution, tests and recovery have not been verified."
)


class DiagnosisService:
    """Mock Manager boundary; callers own orchestration and future persistence policy."""

    def __init__(
        self,
        engine: Engine,
        settings: Settings,
        rag: CodeRag,
        config: DiagnosisSettings | None = None,
        provider: ReasoningProvider | None = None,
        test_fallback: ReasoningProvider | None = None,
    ) -> None:
        self.config = config or DiagnosisSettings()
        if test_fallback is not None and (
            settings.environment != "test" or not self.config.allow_test_fallback
        ):
            raise ValueError("Deterministic fallback requires explicit test environment and opt-in")
        self.provider = provider or (
            OllamaProvider(self.config) if self.config.provider == "ollama" else DisabledProvider()
        )
        self.test_fallback = test_fallback
        self.rag = rag
        self.context = DiagnosisContextRepository(engine, settings)

    def diagnose(self, request: DiagnosisRequest) -> DiagnosisResult:
        """Validate context, retrieve, reason, and reverify citations before returning findings."""
        request = DiagnosisRequest.model_validate(request.model_dump())
        try:
            context = self.context.load(request)
        except ContextRejected as error:
            return self._review(request, str(error))
        except (PersistenceError, ApiError, OSError, ValueError):
            return self._review(request, "CONTEXT_UNAVAILABLE")
        # Parsing arbitrary text as a trace must never fabricate a usable stack frame.
        from app.agents.diagnosis.code_rag.stacktrace import hints

        if context.stack_trace.strip() and not hints(context.stack_trace):
            return self._review(request, "MALFORMED_LOG")
        retrieval = self.rag.retrieve(
            RetrievalRequest(
                application_id=request.application_id,
                repository_revision=request.repository_revision,
                incident_id=request.incident_id,
                run_id=request.run_id,
                error_type=context.error_type,
                error_message=context.error_message,
                stack_trace=context.stack_trace,
                search_query=request.search_query,
                top_k=min(request.top_k, 5),
            )
        )
        if not retrieval.evidence or retrieval.status in {"empty", "unavailable"}:
            return self._review(request, "INSUFFICIENT_EVIDENCE", insufficient=True)
        evidence = retrieval.evidence
        try:
            self._verify(request, evidence)
        except (RagError, PersistenceError, ApiError, OSError, ValueError, KeyError):
            return self._review(request, "INVALID_CITATION")
        reasoning = ReasoningContext(
            error_type=context.error_type,
            error_message=context.error_message,
            stack_trace=context.stack_trace,
            evidence=evidence,
        )
        used_fallback = False
        provider = self.provider
        try:
            raw = provider.reason(reasoning.model_copy(deep=True))
        except Exception:
            if self.test_fallback is None:
                return self._review(request, "LLM_UNAVAILABLE")
            provider, used_fallback = self.test_fallback, True
            try:
                raw = provider.reason(reasoning.model_copy(deep=True))
            except Exception:
                return self._review(request, "TEST_FALLBACK_FAILED")
        try:
            draft = self._validate_draft(raw, evidence)
            # Prevent a provider-time artifact mutation from publishing stale citations.
            self._verify(request, evidence)
        except (
            ValidationError,
            RagError,
            PersistenceError,
            ApiError,
            OSError,
            ValueError,
            KeyError,
            TypeError,
        ):
            return self._review(request, "INVALID_REASONING_OR_CITATION")
        cited = {
            identity for hypothesis in draft.hypotheses for identity in hypothesis.evidence_ids
        }
        selected = [item for item in evidence if item.evidence_id in cited]
        manual = used_fallback or draft.needs_manual_review or retrieval.status == "partial"
        result = DiagnosisResult(
            incident_id=request.incident_id,
            run_id=request.run_id,
            application_id=request.application_id,
            input_revision=request.repository_revision,
            status="manual_review" if manual else "completed",
            outcome="manual_review" if manual else "diagnosed",
            hypothesis="Possible causes: "
            + " | ".join(item.statement for item in draft.hypotheses),
            hypotheses=draft.hypotheses,
            confidence_label="low"
            if manual
            else "medium"
            if draft.confidence_label == "high"
            else draft.confidence_label,
            uncertainty=UNCERTAINTY + " " + draft.uncertainty,
            suggested_direction=draft.suggested_direction,
            evidence=selected,
            facts=self._facts(selected),
            provider=provider.name,
            used_test_fallback=used_fallback,
            error=DiagnosisFailure(
                code="TEST_FALLBACK" if used_fallback else "PARTIAL_RETRIEVAL",
                message="Human review is required.",
            )
            if used_fallback or retrieval.status == "partial"
            else None,
        )
        LOGGER.info("Diagnosis reasoning returned", extra={"status": result.status})
        return result

    def _verify(self, request: DiagnosisRequest, evidence: list[RetrievedEvidence]) -> None:
        if len({item.evidence_id for item in evidence}) != len(evidence):
            raise ValueError("Duplicate citation identity")
        for item in evidence:
            resolved = self.rag.evidence.resolve(
                request.application_id,
                request.repository_revision,
                item.source_snapshot_ref,
                item.evidence_id,
            )
            if any(
                resolved[key] != value
                for key, value in item.model_dump().items()
                if key in resolved
            ):
                raise ValueError("Citation metadata does not match stored source")

    def _validate_draft(self, raw: str, evidence: list[RetrievedEvidence]) -> ReasoningDraft:
        if not isinstance(raw, str) or len(raw.encode()) > self.config.max_response_bytes:
            raise ValueError("Unbounded provider output")
        draft = ReasoningDraft.model_validate_json(raw)
        identities = {item.evidence_id for item in evidence}
        for hypothesis in draft.hypotheses:
            if (
                len(set(hypothesis.evidence_ids)) != len(hypothesis.evidence_ids)
                or not set(hypothesis.evidence_ids) <= identities
            ):
                raise ValueError("Unknown citation identity")
        text = "\n".join(
            [
                draft.uncertainty,
                draft.suggested_direction,
                *(
                    value
                    for item in draft.hypotheses
                    for value in (item.statement, item.uncertainty)
                ),
            ]
        )
        if (
            not text.strip()
            or redact(text) != text
            or "```" in text
            or "-----BEGIN " in text
            or "diff --git" in text
            or "*** Begin Patch" in text
            or any(ord(character) < 32 and character not in "\n\r\t" for character in text)
        ):
            raise ValueError("Unsafe reasoning output")
        if (
            any(
                not item.statement.strip() or not item.uncertainty.strip()
                for item in draft.hypotheses
            )
            or not draft.uncertainty.strip()
            or not draft.suggested_direction.strip()
        ):
            raise ValueError("Reasoning requires explicit uncertainty")
        return draft

    def _facts(self, evidence: list[RetrievedEvidence]) -> list[EvidenceFact]:
        return [
            EvidenceFact(
                evidence_id=item.evidence_id,
                observation=(
                    f"Verified {item.file_path}:{item.start_line}-{item.end_line} "
                    "at the requested revision; "
                )
                + (
                    "stack line matched."
                    if item.exact_tier == 2
                    else "retrieved source context, not proof of causation."
                ),
            )
            for item in evidence
        ]

    def _review(
        self,
        request: DiagnosisRequest,
        code: str,
        *,
        insufficient: bool = False,
        evidence: list[RetrievedEvidence] | None = None,
    ) -> DiagnosisResult:
        return DiagnosisResult(
            incident_id=request.incident_id,
            run_id=request.run_id,
            application_id=request.application_id,
            input_revision=request.repository_revision,
            status="manual_review",
            outcome="insufficient_evidence" if insufficient else "manual_review",
            hypothesis="No supported root-cause hypothesis is available.",
            confidence_label="low",
            uncertainty=UNCERTAINTY + " The available reasoning or evidence is insufficient.",
            suggested_direction="Review the incident, exact revision and source evidence manually.",
            evidence=evidence or [],
            facts=self._facts(evidence or []),
            provider=self.provider.name,
            error=DiagnosisFailure(code=code, message="Diagnosis requires human review."),
        )
