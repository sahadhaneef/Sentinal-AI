"""Internal classification only; existing public and Manager envelopes are unchanged."""

from enum import StrEnum

from app.schemas.common import WireModel


class FailureKind(StrEnum):
    TRANSIENT_PROVIDER = "transient_provider"
    NETWORK = "temporary_network"
    PROVIDER_TIMEOUT = "provider_timeout"
    CONFIGURATION = "configuration"
    PROVIDER_RESPONSE = "invalid_provider_response"
    PROVIDER_UNKNOWN = "unclassified_provider_failure"
    INVALID_REQUEST = "invalid_request"
    CONTEXT = "context_unavailable"
    REVISION = "invalid_revision"
    ARTIFACT = "invalid_artifact"
    INSUFFICIENT = "insufficient_evidence"
    CONFLICT = "conflicting_evidence"
    CITATION = "invalid_citation"
    CANCELLED = "cancelled"
    DEADLINE = "stage_timeout"
    STARTUP = "worker_startup_failure"
    WORKER = "worker_process_failure"
    BUSY = "worker_capacity"


class ExecutionFailure(WireModel):
    """Eligibility is derived, never accepted as an untrusted boolean override."""

    kind: FailureKind

    @property
    def retry_eligible(self) -> bool:
        """Manager may retry once within the same deadline; Diagnosis never retries."""
        return self.kind in {
            FailureKind.TRANSIENT_PROVIDER,
            FailureKind.NETWORK,
            FailureKind.PROVIDER_TIMEOUT,
        }


def classify_review(code: str) -> ExecutionFailure:
    """Fail closed for unknown review codes and never infer transient provider errors."""
    if code in {"CONTEXT_SCOPE_MISMATCH", "REVISION_UNAVAILABLE", "SCOPE_MISMATCH"}:
        kind = FailureKind.REVISION
    elif code in {"LOG_SCOPE_MISMATCH", "LOG_SCOPE"}:
        kind = FailureKind.ARTIFACT
    elif code == "CONTEXT_UNAVAILABLE":
        kind = FailureKind.CONTEXT
    elif code == "MALFORMED_LOG":
        kind = FailureKind.INVALID_REQUEST
    elif code in {"CONFLICTING_ERROR_TYPES", "CONFLICTING_SNAPSHOTS", "INCIDENT_INPUT_CONFLICT"}:
        kind = FailureKind.CONFLICT
    elif "CITATION" in code or code == "INVALID_REASONING_OR_CITATION":
        kind = FailureKind.CITATION
    elif code == "LLM_UNAVAILABLE":
        kind = FailureKind.PROVIDER_UNKNOWN
    else:
        kind = FailureKind.INSUFFICIENT
    return ExecutionFailure(kind=kind)
