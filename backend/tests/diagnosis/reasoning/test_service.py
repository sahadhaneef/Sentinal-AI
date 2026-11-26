"""Diagnosis success/failure paths use real scoped D1 citations without workflow writes."""

from collections.abc import Callable

import pytest
from pydantic import ValidationError
from sqlalchemy import MetaData, Table, func, inspect, select

from app.agents.diagnosis.code_rag.contracts import RetrievalRequest, RetrievalResult
from app.agents.diagnosis.reasoning.config import DiagnosisSettings
from app.agents.diagnosis.reasoning.contracts import DiagnosisRequest
from app.agents.diagnosis.reasoning.service import DiagnosisService
from app.models import Artifact
from app.repositories.unit_of_work import transaction
from app.schemas.domain import Diagnosis
from tests.diagnosis.reasoning.conftest import FixtureReasoner, Scenario


def retrieved(scenario: Scenario) -> RetrievalResult:
    return scenario.harness.service.retrieve(
        RetrievalRequest.model_validate(
            scenario.request.model_dump() | {"stack_trace_ref": "d2_log"}
        )
    )


def test_success_uses_real_citations_and_preserves_public_schema(scenario: Scenario) -> None:
    with scenario.harness.engine.connect() as connection:
        tables = inspect(connection).get_table_names()
        before = {
            name: connection.scalar(
                select(func.count()).select_from(Table(name, MetaData(), autoload_with=connection))
            )
            for name in tables
        }
    result = scenario.service.diagnose(scenario.request)
    assert result.status == "completed" and result.outcome == "diagnosed"
    assert result.confidence_label == "medium" and result.hypothesis.startswith("Possible causes:")
    assert "not been verified" in result.uncertainty
    assert result.evidence[0].file_path == "app.py" and result.evidence[0].start_line == 1
    assert result.hypotheses[0].evidence_ids == [result.facts[0].evidence_id]
    assert isinstance(result.to_public(), Diagnosis)
    assert result.model_dump()["evidence"][0]["evidence_id"] == result.hypotheses[0].evidence_ids[0]
    with scenario.harness.engine.connect() as connection:
        after = {
            name: connection.scalar(
                select(func.count()).select_from(Table(name, MetaData(), autoload_with=connection))
            )
            for name in tables
        }
    assert before == after


@pytest.mark.parametrize(
    ("model_requests_review", "direction", "expected_status"),
    [
        (False, "Inspect the profile at the failing lookup.", "completed"),
        (True, "Inspect the profile at the failing lookup.", "manual_review"),
        (False, " ", "manual_review"),
    ],
)
def test_bounded_diagnosis_respects_model_review_and_requires_direction(
    scenario: Scenario, model_requests_review: bool, direction: str, expected_status: str
) -> None:
    scenario.provider.transform = lambda payload: (
        payload
        | {
            "needs_manual_review": model_requests_review,
            "uncertainty": "The upstream origin of the missing key is unknown.",
            "suggested_direction": direction,
        }
    )
    result = scenario.service.diagnose(scenario.request)
    assert result.status == expected_status
    if direction.strip():
        assert "upstream origin" in result.uncertainty
        assert result.hypotheses[0].evidence_ids == [result.evidence[0].evidence_id]
    else:
        assert result.error is not None
        assert result.error.code == "INVALID_REASONING_OR_CITATION"


@pytest.mark.parametrize(
    "changes",
    [
        {"repository_revision": "wrong"},
        {"application_id": "other"},
        {"run_id": "unknown"},
        {"incident_id": "unknown"},
        {"error_message": "Conflicting caller observation"},
        {"stack_trace_ref": "unrelated_log"},
    ],
)
def test_incorrect_context_never_calls_llm(scenario: Scenario, changes: dict) -> None:
    result = scenario.service.diagnose(scenario.request.model_copy(update=changes))
    assert result.status == "manual_review" and result.error is not None
    assert scenario.provider.calls == 0


def test_insufficient_source(scenario_factory: Callable[..., Scenario]) -> None:
    scenario = scenario_factory(empty_source=True)
    result = scenario.service.diagnose(scenario.request)
    assert result.outcome == "insufficient_evidence" and result.evidence == []
    assert scenario.provider.calls == 0


@pytest.mark.parametrize("trace", ["not a stack trace", "\x00malformed", "x" * 16001])
def test_malformed_logs(scenario_factory: Callable[..., Scenario], trace: str) -> None:
    scenario = scenario_factory(trace=trace)
    result = scenario.service.diagnose(scenario.request)
    assert result.status == "manual_review" and result.error.code == "MALFORMED_LOG"
    assert scenario.provider.calls == 0


def test_invalid_model_citation_rejected(scenario: Scenario) -> None:
    def invent(value: dict) -> dict:
        value["hypotheses"][0]["evidence_ids"] = ["invented"]
        return value

    scenario.provider.transform = invent
    result = scenario.service.diagnose(scenario.request)
    assert result.status == "manual_review" and result.hypotheses == [] and result.evidence == []
    assert result.error.code == "INVALID_REASONING_OR_CITATION"


@pytest.mark.parametrize(
    "field,value",
    [
        ("uncertainty", ""),
        ("hypotheses", []),
        ("suggested_direction", "```python\nexecute()\n```"),
        ("unexpected", "field"),
        ("suggested_direction", "api_key=private"),
    ],
)
def test_invalid_or_unsafe_reasoning(scenario: Scenario, field: str, value: object) -> None:
    scenario.provider.transform = lambda payload: payload | {field: value}
    result = scenario.service.diagnose(scenario.request)
    assert result.status == "manual_review" and not result.hypotheses


def test_llm_failure_is_not_silent_deterministic_success(scenario: Scenario) -> None:
    scenario.provider.fail = True
    result = scenario.service.diagnose(scenario.request)
    assert result.status == "manual_review" and result.error.code == "LLM_UNAVAILABLE"
    assert not result.used_test_fallback and "private provider" not in result.model_dump_json()


def test_explicit_test_fallback_is_repeatable_and_marked(scenario: Scenario) -> None:
    scenario.provider.fail = True
    fallback = FixtureReasoner()
    service = DiagnosisService(
        scenario.harness.engine,
        scenario.harness.settings,
        scenario.harness.service,
        config=DiagnosisSettings(allow_test_fallback=True),
        provider=scenario.provider,
        test_fallback=fallback,
    )
    first, second = service.diagnose(scenario.request), service.diagnose(scenario.request)
    assert first.used_test_fallback and first.status == "manual_review"
    assert first.confidence_label == "low" and first.error.code == "TEST_FALLBACK"
    assert first.hypotheses == second.hypotheses and first.evidence == second.evidence
    scenario.harness.settings.environment = "local"
    with pytest.raises(ValueError, match="test environment"):
        DiagnosisService(
            scenario.harness.engine,
            scenario.harness.settings,
            scenario.harness.service,
            config=DiagnosisSettings(allow_test_fallback=True),
            test_fallback=fallback,
        )


def test_post_provider_artifact_tampering_drops_citations(scenario: Scenario) -> None:
    evidence = retrieved(scenario).evidence[0]
    with transaction(scenario.harness.engine) as store:
        artifact = store.records(Artifact).get(evidence.artifact_id)

    def tamper() -> None:
        (scenario.harness.settings.artifact_root / artifact.storage_key).write_bytes(b"changed")

    scenario.provider.callback = tamper
    result = scenario.service.diagnose(scenario.request)
    assert result.status == "manual_review" and result.evidence == [] and result.hypotheses == []


def test_invalid_retriever_metadata_is_reverified(
    scenario: Scenario, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = retrieved(scenario)
    original.evidence[0].end_line = 999
    monkeypatch.setattr(scenario.harness.service, "retrieve", lambda request: original)
    result = scenario.service.diagnose(scenario.request)
    assert result.status == "manual_review" and result.error.code == "INVALID_CITATION"
    assert scenario.provider.calls == 0


def test_partial_retrieval_always_requires_review(
    scenario: Scenario, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = retrieved(scenario)
    original.status = "partial"
    monkeypatch.setattr(scenario.harness.service, "retrieve", lambda request: original)
    result = scenario.service.diagnose(scenario.request)
    assert result.status == "manual_review" and result.error.code == "PARTIAL_RETRIEVAL"


def test_invalid_mock_manager_request() -> None:
    with pytest.raises(ValidationError):
        DiagnosisRequest(
            incident_id="incident",
            run_id="run",
            application_id="app",
            repository_revision="../escape",
        )
    with pytest.raises(ValidationError):
        DiagnosisRequest(
            incident_id="incident",
            run_id="run",
            application_id="app",
            repository_revision="r1",
            stack_trace="\x00invalid",
        )
