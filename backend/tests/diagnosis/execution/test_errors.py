"""Explicit provider errors are classified without changing the D3 result envelope."""

import urllib.error
from io import BytesIO

import pytest

from app.agents.diagnosis.execution.errors import ExecutionFailure, FailureKind, classify_review
from app.agents.diagnosis.reasoning.config import DiagnosisSettings
from app.agents.diagnosis.reasoning.contracts import ReasoningContext
from app.agents.diagnosis.reasoning.providers import (
    DisabledProvider,
    OllamaProvider,
    ReasoningUnavailable,
)


@pytest.mark.parametrize(
    "error,kind,retry",
    [
        (
            urllib.error.HTTPError("http://127.0.0.1", 503, "unavailable", {}, BytesIO()),
            FailureKind.TRANSIENT_PROVIDER,
            True,
        ),
        (
            urllib.error.HTTPError("http://127.0.0.1", 404, "missing", {}, BytesIO()),
            FailureKind.CONFIGURATION,
            False,
        ),
        (TimeoutError(), FailureKind.PROVIDER_TIMEOUT, True),
        (urllib.error.URLError(ConnectionRefusedError()), FailureKind.NETWORK, True),
        (urllib.error.URLError(TimeoutError()), FailureKind.PROVIDER_TIMEOUT, True),
        (ValueError("private payload"), FailureKind.PROVIDER_RESPONSE, False),
    ],
)
def test_transport_failure_classification(
    monkeypatch: pytest.MonkeyPatch, error: Exception, kind: FailureKind, retry: bool
) -> None:
    provider = OllamaProvider(DiagnosisSettings(provider="ollama", model="test-only"))

    def fail(*args: object, **kwargs: object) -> None:
        raise error

    monkeypatch.setattr(provider.opener, "open", fail)
    with pytest.raises(ReasoningUnavailable) as caught:
        provider.reason(
            ReasoningContext(
                error_type="KeyError", error_message="missing", stack_trace="", evidence=[]
            )
        )
    assert caught.value.kind == kind
    failure = ExecutionFailure(kind=kind)
    assert failure.retry_eligible is retry
    assert ExecutionFailure.model_validate_json(failure.model_dump_json()).kind == kind
    assert "private payload" not in str(caught.value)


def test_disabled_provider_is_permanent() -> None:
    with pytest.raises(ReasoningUnavailable) as caught:
        DisabledProvider().reason(
            ReasoningContext(error_type="", error_message="", stack_trace="", evidence=[])
        )
    assert caught.value.kind == FailureKind.CONFIGURATION


@pytest.mark.parametrize(
    "code",
    [
        "INVALID_CITATION",
        "INSUFFICIENT_EVIDENCE",
        "CONFLICTING_ERROR_TYPES",
        "CONTEXT_SCOPE_MISMATCH",
        "LOG_SCOPE_MISMATCH",
        "LLM_UNAVAILABLE",
        "unknown",
    ],
)
def test_evidence_and_unknown_failures_are_never_retryable(code: str) -> None:
    assert not classify_review(code).retry_eligible
