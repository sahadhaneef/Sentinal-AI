"""Injected read boundaries retain existing scoped standalone behavior."""

import threading
from time import monotonic

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.agents.diagnosis.code_rag.service import CodeRag
from app.agents.diagnosis.execution.control import ExecutionControl, ExecutionStopped
from app.agents.diagnosis.execution.standalone import StandaloneFactory
from app.agents.diagnosis.quality.service import QualityDiagnosisService
from app.agents.diagnosis.reasoning.repository import DiagnosisContextRepository
from app.agents.diagnosis.repositories import RegisteredRevision, RetrievalRepositories
from tests.diagnosis.reasoning.conftest import Scenario


def test_injected_repositories_preserve_citations_and_scope(scenario: Scenario) -> None:
    base = scenario.harness.service
    repositories = RetrievalRepositories(base.catalog, base.evidence, base.repositories.index)
    rag = CodeRag(
        scenario.harness.engine,
        scenario.harness.settings,
        scenario.harness.rag,
        scenario.harness.encoder,
        repositories=repositories,
    )
    context = DiagnosisContextRepository(scenario.harness.engine, scenario.harness.settings)
    service = QualityDiagnosisService(
        scenario.harness.engine,
        scenario.harness.settings,
        rag,
        provider=scenario.provider,
        context_repository=context,
    )
    value = service.diagnose(scenario.request)
    assert value.result.status == "completed" and value.result.evidence
    revision = repositories.source.revision("rag_app", "r1")
    assert isinstance(revision, RegisteredRevision) and revision.snapshot_artifact_id
    assert not hasattr(revision, "_sa_instance_state")
    wrong = scenario.request.model_copy(update={"repository_revision": "wrong"})
    assert service.diagnose(wrong).result.error.code == "CONTEXT_SCOPE_MISMATCH"
    foreign = scenario.request.model_copy(update={"stack_trace_ref": "foreign_log"})
    assert service.diagnose(foreign).result.error.code == "LOG_SCOPE_MISMATCH"


def test_standalone_worker_factory_disables_domain_writes(scenario: Scenario) -> None:
    factory = StandaloneFactory.from_settings(scenario.harness.settings, scenario.harness.rag)
    with factory(ExecutionControl(), lambda error: None) as diagnose:
        service = diagnose.__self__
        with pytest.raises(OperationalError), service.engine.begin() as connection:
            connection.execute(text("UPDATE incidents SET message = 'not allowed'"))


@pytest.mark.parametrize("expired", [False, True])
def test_checkpoint_stops_before_context_loading(scenario: Scenario, expired: bool) -> None:
    event = threading.Event()
    if not expired:
        event.set()
    control = ExecutionControl(monotonic() - 1 if expired else monotonic() + 10, event)
    rag = CodeRag(
        scenario.harness.engine,
        scenario.harness.settings,
        scenario.harness.rag,
        scenario.harness.encoder,
        control=control,
    )
    service = QualityDiagnosisService(
        scenario.harness.engine,
        scenario.harness.settings,
        rag,
        provider=scenario.provider,
        control=control,
    )
    with pytest.raises(ExecutionStopped) as caught:
        service.diagnose(scenario.request)
    assert caught.value.code == ("STAGE_TIMEOUT" if expired else "CANCELLED")
    assert scenario.provider.calls == 0


def test_mismatched_execution_controls_are_rejected(scenario: Scenario) -> None:
    with pytest.raises(ValueError, match="Share one ExecutionControl"):
        QualityDiagnosisService(
            scenario.harness.engine,
            scenario.harness.settings,
            scenario.harness.service,
            control=ExecutionControl(monotonic() + 10),
        )
