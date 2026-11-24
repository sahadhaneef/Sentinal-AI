"""Tampered citations, narrative hallucinations, provenance, and optional audit writes."""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.agents.diagnosis.quality.manager_adapter import from_manager, to_manager
from app.agents.diagnosis.quality.recording import OutcomeRecorder
from app.agents.diagnosis.quality.service import QualityDiagnosisService
from app.models import AuditEvent
from app.repositories.unit_of_work import transaction
from tests.diagnosis.reasoning.conftest import Scenario
from tests.diagnosis.reasoning.test_service import retrieved


def service(scenario: Scenario) -> QualityDiagnosisService:
    return QualityDiagnosisService(
        scenario.harness.engine,
        scenario.harness.settings,
        scenario.harness.service,
        provider=scenario.provider,
    )


def test_quality_keeps_facts_hypotheses_provenance_and_source_unchanged(scenario: Scenario) -> None:
    path = scenario.harness.root / "app.py"
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    checked = service(scenario).diagnose(scenario.request)
    assert checked.result.status == "completed" and not checked.assessment.issues
    assert (
        checked.provenance.repository_revision == "r1"
        and checked.provenance.query_hash.startswith("sha256:")
    )
    assert checked.provenance.citations[0].content_hash == checked.result.evidence[0].content_hash
    assert checked.result.hypotheses[0].evidence_ids == checked.assessment.verified_evidence_ids
    assert before == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "field,value",
    [
        ("file_path", "../escape.py"),
        ("file_path", "C:/private.py"),
        ("file_path", "invented.py"),
        ("start_line", 0),
        ("end_line", 999),
        ("symbol", "invented"),
        ("repository_revision", "other"),
        ("content_hash", "sha256:" + "0" * 64),
        ("source_snapshot_ref", "wrong"),
        ("source_file_ref", "wrong"),
    ],
)
def test_unverifiable_ranges_and_references_never_reach_llm(
    scenario: Scenario, monkeypatch: pytest.MonkeyPatch, field: str, value: object
) -> None:
    original = retrieved(scenario)
    original.evidence[0] = original.evidence[0].model_copy(update={field: value})
    monkeypatch.setattr(scenario.harness.service, "retrieve", lambda request: original)
    checked = service(scenario).diagnose(scenario.request)
    assert checked.result.status == "manual_review" and scenario.provider.calls == 0
    assert checked.assessment.issues[0].code == "UNVERIFIABLE_CITATION"


@pytest.mark.parametrize(
    "statement,code",
    [
        ("The failure originates in imaginary.py:900.", "NARRATIVE_CITATION_INVALID"),
        ("The failure originates in app.py:900.", "NARRATIVE_CITATION_INVALID"),
        ("The failure originates in app.py line 900.", "NARRATIVE_CITATION_INVALID"),
        ("The failure originates in config.yaml:900.", "NARRATIVE_CITATION_INVALID"),
        ("This is definitely the proven root cause.", "UNSUPPORTED_CERTAINTY"),
        ("I ran the tests and all tests passed.", "UNSUPPORTED_EXECUTION_CLAIM"),
        ("The patch was applied and recovery was verified.", "UNSUPPORTED_EXECUTION_CLAIM"),
    ],
)
def test_unsupported_narrative_claims_require_review(
    scenario: Scenario, statement: str, code: str
) -> None:
    def alter(payload: dict) -> dict:
        payload["hypotheses"][0]["statement"] = statement
        return payload

    scenario.provider.transform = alter
    checked = service(scenario).diagnose(scenario.request)
    assert checked.result.status == "manual_review" and checked.result.hypotheses == []
    assert code in [issue.code for issue in checked.assessment.issues]


def test_outcome_recording_is_explicit_and_excludes_source_text(scenario: Scenario) -> None:
    checked = service(scenario).diagnose(scenario.request)
    with transaction(scenario.harness.engine) as store:
        assert store.session.scalar(select(func.count()).select_from(AuditEvent)) == 0
    event_id = OutcomeRecorder(scenario.harness.engine).record(checked)
    with transaction(scenario.harness.engine) as store:
        event = store.records(AuditEvent).get(event_id)
        assert event.event_type == "diagnosis_quality_reviewed"
        assert event.payload_metadata["input_revision"] == "r1"
        assert "return profile" not in json.dumps(event.payload_metadata)
        assert "stack_trace" not in json.dumps(event.payload_metadata)
    checked.result.input_revision = "wrong"
    with pytest.raises(ValueError, match="scope"):
        OutcomeRecorder(scenario.harness.engine).record(checked)


def test_citation_claims_in_uncertainty_are_checked(scenario: Scenario) -> None:
    scenario.provider.transform = lambda payload: payload | {"uncertainty": "See imaginary.py:800."}
    checked = service(scenario).diagnose(scenario.request)
    assert checked.result.status == "manual_review"
    assert checked.result.error.code == "NARRATIVE_CITATION_INVALID"
    assert "imaginary.py" not in checked.result.model_dump_json()


def test_valid_narrative_source_range_is_retained(scenario: Scenario) -> None:
    def cite(payload: dict) -> dict:
        payload["hypotheses"][0]["statement"] = "A missing name key is plausible at app.py:2."
        return payload

    scenario.provider.transform = cite
    checked = service(scenario).diagnose(scenario.request)
    assert checked.result.status == "completed" and not checked.assessment.issues


@dataclass
class ManagerInputFixture:
    incident_id: str
    run_id: str
    repository_revision: str
    extra: dict[str, Any] = field(default_factory=dict)


def test_manager_wire_mapping_preserves_ids_revision_and_evidence(scenario: Scenario) -> None:
    wire = ManagerInputFixture(
        scenario.request.incident_id, scenario.request.run_id, "r1", {"application_id": "rag_app"}
    )
    request = from_manager(wire)
    assert request == scenario.request
    checked = service(scenario).diagnose(request)
    output = to_manager(checked, 10)
    assert output.success and output.data["status"] == "completed"
    assert output.data["evidence"][0]["repository_revision"] == "r1"
    assert "outcome" not in output.data and "incident_id" not in output.data
    wire.repository_revision = "HEAD"
    with pytest.raises(ValueError, match="exact revision"):
        from_manager(wire)
    wire.repository_revision = "r1"
    wire.extra = {}
    with pytest.raises(ValidationError):
        from_manager(wire)


def test_manager_failure_mapping_is_sanitized(scenario: Scenario) -> None:
    scenario.provider.fail = True
    checked = service(scenario).diagnose(scenario.request)
    output = to_manager(checked, 10)
    assert not output.success and output.error == "LLM_UNAVAILABLE" and output.data == {}
