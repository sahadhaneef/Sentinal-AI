"""Actual D1 retrieval and existing domain context with deterministic reasoning fixtures."""

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from app.agents.diagnosis.code_rag.hashing import digest
from app.agents.diagnosis.reasoning.contracts import DiagnosisRequest, ReasoningContext
from app.agents.diagnosis.reasoning.service import DiagnosisService
from app.db.types import utc_now
from app.models import Artifact, WorkflowRun
from app.models.enums import RunState
from app.repositories.incident import MonitoringInput
from app.repositories.unit_of_work import transaction
from tests.diagnosis.conftest import Harness


def draft(context: ReasoningContext) -> dict:
    """Synthetic source-grounded response for isolated tests, never a live LLM result."""
    return {
        "hypotheses": [
            {
                "statement": "The signup profile may lack the directly accessed name key.",
                "evidence_ids": [context.evidence[0].evidence_id],
                "uncertainty": "The runtime profile payload is not available.",
            }
        ],
        "confidence_label": "high",
        "uncertainty": "Other input validation paths may contribute.",
        "suggested_direction": (
            "Review the input contract and the missing field at this source range."
        ),
        "needs_manual_review": False,
    }


class FixtureReasoner:
    """Explicit deterministic test provider; not installed as a runtime fallback."""

    name = "test-fixture-only"

    def __init__(self) -> None:
        self.calls = 0
        self.fail = False
        self.transform: Callable[[dict], dict] = lambda value: value
        self.context: ReasoningContext | None = None
        self.callback: Callable[[], None] = lambda: None

    def reason(self, context: ReasoningContext) -> str:
        import json

        self.calls += 1
        self.context = context
        self.callback()
        if self.fail:
            raise RuntimeError("private provider error must not leak")
        return json.dumps(self.transform(draft(context)))


@dataclass
class Scenario:
    harness: Harness
    request: DiagnosisRequest
    provider: FixtureReasoner
    service: DiagnosisService


@pytest.fixture
def scenario_factory(harness: Harness) -> Callable[..., Scenario]:
    def create(
        trace: str = 'File "app.py", line 2, in register\nKeyError: name',
        empty_source: bool = False,
    ) -> Scenario:
        if not empty_source:
            (harness.root / "app.py").write_bytes(
                b'def register(profile):\n    return profile["name"]\n'
            )
        harness.service.index("rag_app", "r1")
        log = trace.encode()
        harness.settings.artifact_root.mkdir(parents=True, exist_ok=True)
        (harness.settings.artifact_root / "incident.log").write_bytes(log)
        with transaction(harness.engine) as store:
            store.records(Artifact).add(
                Artifact(
                    id="d2_log",
                    kind="log",
                    storage_key="incident.log",
                    sha256=digest(log),
                    size_bytes=len(log),
                    content_type="text/plain",
                    redacted=True,
                )
            )
            _, incident = store.incidents.record_monitoring_event(
                MonitoringInput(
                    application_id="rag_app",
                    repository_revision="r1",
                    source_event_id="d2_event",
                    fingerprint=digest(b"d2 fixture"),
                    severity="high",
                    error_type="KeyError",
                    message="Missing profile name",
                    occurred_at=utc_now(),
                    log_artifact_id="d2_log",
                )
            )
            store.records(WorkflowRun).add(
                WorkflowRun(
                    id="d2_run",
                    incident_id=incident.id,
                    application_id="rag_app",
                    repository_revision="r1",
                    state=RunState.DIAGNOSING,
                )
            )
        request = DiagnosisRequest(
            incident_id=incident.id,
            run_id="d2_run",
            application_id="rag_app",
            repository_revision="r1",
        )
        provider = FixtureReasoner()
        return Scenario(
            harness,
            request,
            provider,
            DiagnosisService(
                harness.engine,
                harness.settings,
                harness.service,
                provider=provider,
            ),
        )

    return create


@pytest.fixture
def scenario(scenario_factory: Callable[..., Scenario]) -> Scenario:
    return scenario_factory()
