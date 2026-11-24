"""Pinned Manager-shaped fixtures, not registration or shared-database integration."""

import asyncio
import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select

from app.agents.diagnosis.quality.manager_adapter import from_manager, to_manager
from app.agents.diagnosis.quality.manager_invocation import invoke_manager_request
from app.models import AuditEvent, Diagnosis, WorkflowRun
from app.repositories.unit_of_work import transaction
from tests.diagnosis.quality.test_quality import service
from tests.diagnosis.reasoning.conftest import Scenario


@dataclass
class AgentInputFixture:
    """Shape inspected at manager-backend b74f09a, without importing its runtime."""

    incident_id: str
    run_id: str
    repository_revision: str
    extra: dict[str, Any] = field(default_factory=dict)


def wire(scenario: Scenario) -> AgentInputFixture:
    return AgentInputFixture(
        scenario.request.incident_id,
        scenario.request.run_id,
        scenario.request.repository_revision,
        {"application_id": scenario.request.application_id},
    )


def test_invocation_success_preserves_source_and_database(scenario: Scenario) -> None:
    path = scenario.harness.root / "app.py"
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with transaction(scenario.harness.engine) as store:
        counts = [
            store.session.scalar(select(func.count()).select_from(model))
            for model in (Diagnosis, AuditEvent, WorkflowRun)
        ]
    checked = service(scenario).diagnose(scenario.request)
    callback = AsyncMock(return_value=checked)
    output = asyncio.run(invoke_manager_request(wire(scenario), callback))
    assert output.success and output.data["status"] == "completed"
    assert output.data["evidence"][0]["repository_revision"] == "r1"
    assert set(output.model_dump()) == {"success", "data", "error", "duration_ms"}
    assert "incident_id" not in output.data and "outcome" not in output.data
    assert callback.await_args.args[0] == scenario.request
    assert before == hashlib.sha256(path.read_bytes()).hexdigest()
    with transaction(scenario.harness.engine) as store:
        assert counts == [
            store.session.scalar(select(func.count()).select_from(model))
            for model in (Diagnosis, AuditEvent, WorkflowRun)
        ]


def test_insufficient_evidence_maps_to_review(scenario_factory: Any) -> None:
    scenario = scenario_factory(empty_source=True)
    checked = service(scenario).diagnose(scenario.request)
    output = asyncio.run(invoke_manager_request(wire(scenario), AsyncMock(return_value=checked)))
    assert output.success and output.data["status"] == "manual_review"
    assert output.data["evidence"] == [] and scenario.provider.calls == 0


def test_provider_failure_does_not_select_retry_policy(scenario: Scenario) -> None:
    scenario.provider.fail = True
    checked = service(scenario).diagnose(scenario.request)
    callback = AsyncMock(return_value=checked)
    output = asyncio.run(invoke_manager_request(wire(scenario), callback))
    assert not output.success and output.error == "LLM_UNAVAILABLE" and not output.data
    assert callback.await_count == 1
    assert "retryable" not in output.model_dump()


@pytest.mark.parametrize("revision", ["HEAD", "main", "latest", "../outside", ""])
def test_invalid_revisions_do_not_invoke_service(scenario: Scenario, revision: str) -> None:
    value = wire(scenario)
    value.repository_revision = revision
    callback = AsyncMock()
    with pytest.raises(ValueError, match="Invalid Manager diagnosis request"):
        asyncio.run(invoke_manager_request(value, callback))
    callback.assert_not_awaited()


def test_log_translation_and_unknown_fields(scenario: Scenario) -> None:
    value = wire(scenario)
    value.extra.update(
        source_log='File "app.py", line 2, in register\nKeyError: name',
        error_type="KeyError",
        error_message="Missing profile name",
        stack_trace_ref="d2_log",
    )
    request = from_manager(asdict(value))
    assert request.stack_trace == value.extra["source_log"]
    assert request.stack_trace_ref == "d2_log" and request.error_type == "KeyError"
    value.extra["unapproved_field"] = "private-value"
    with pytest.raises(ValueError) as caught:
        asyncio.run(invoke_manager_request(value, AsyncMock()))
    assert "private-value" not in str(caught.value)


@pytest.mark.parametrize("field", ["incident_id", "run_id", "application_id", "input_revision"])
def test_cross_request_results_rejected(scenario: Scenario, field: str) -> None:
    checked = service(scenario).diagnose(scenario.request)
    setattr(checked.result, field, "other")
    with pytest.raises(ValueError, match="Invalid Diagnosis response"):
        asyncio.run(invoke_manager_request(wire(scenario), AsyncMock(return_value=checked)))


@pytest.mark.parametrize(
    "field,value",
    [
        ("start_line", 0),
        ("end_line", 999),
        ("file_path", "invented.py"),
        ("content_hash", "sha256:" + "0" * 64),
        ("repository_revision", "other"),
    ],
)
def test_changed_citation_rejected(scenario: Scenario, field: str, value: object) -> None:
    checked = service(scenario).diagnose(scenario.request)
    setattr(checked.result.evidence[0], field, value)
    with pytest.raises(ValueError):
        to_manager(checked, 1)


@pytest.mark.parametrize(
    "mutation", ["provenance", "verified", "hypothesis", "duplicate", "status"]
)
def test_inconsistent_quality_envelopes_rejected(scenario: Scenario, mutation: str) -> None:
    checked = service(scenario).diagnose(scenario.request)
    if mutation == "provenance":
        checked.provenance.citations.clear()
    elif mutation == "verified":
        checked.assessment.verified_evidence_ids.clear()
    elif mutation == "hypothesis":
        checked.result.hypotheses[0].evidence_ids = ["invented"]
    elif mutation == "duplicate":
        checked.result.evidence.append(checked.result.evidence[0])
    else:
        checked.result.outcome = "insufficient_evidence"
    with pytest.raises(ValueError):
        to_manager(checked, 1)


def test_cooperative_cancellation_and_late_result_rejection(scenario: Scenario) -> None:
    checked = service(scenario).diagnose(scenario.request)

    async def exercise(suppress: bool) -> None:
        entered = asyncio.Event()
        finalized = asyncio.Event()

        async def callback(request: Any) -> Any:
            entered.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                if not suppress:
                    raise
                return checked
            finally:
                finalized.set()

        task = asyncio.create_task(invoke_manager_request(wire(scenario), callback))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert finalized.is_set()

    asyncio.run(exercise(False))
    asyncio.run(exercise(True))


def test_caller_timeout_remains_caller_owned(scenario: Scenario) -> None:
    async def callback(request: Any) -> Any:
        await asyncio.Event().wait()

    async def exercise() -> None:
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(invoke_manager_request(wire(scenario), callback), timeout=0.01)

    asyncio.run(exercise())


def test_sync_service_is_rejected_before_execution(scenario: Scenario) -> None:
    with pytest.raises(TypeError, match="cooperative async"):
        asyncio.run(invoke_manager_request(wire(scenario), service(scenario).diagnose))
    assert scenario.provider.calls == 0


def test_callback_failure_does_not_leak_private_details(scenario: Scenario) -> None:
    callback = AsyncMock(side_effect=RuntimeError("private credential in provider response"))
    with pytest.raises(RuntimeError, match="^Diagnosis invocation failed$"):
        asyncio.run(invoke_manager_request(wire(scenario), callback))
    assert callback.await_count == 1


def test_callback_cannot_change_correlation_anchor(scenario: Scenario) -> None:
    checked = service(scenario).diagnose(scenario.request)

    async def callback(request: Any) -> Any:
        request.run_id = "other"
        checked.result.run_id = "other"
        return checked

    with pytest.raises(ValueError, match="Invalid Diagnosis response"):
        asyncio.run(invoke_manager_request(wire(scenario), callback))


def test_unknown_registered_revision_is_not_a_success(scenario: Scenario) -> None:
    request = scenario.request.model_copy(update={"repository_revision": "unknown_revision"})
    checked = service(scenario).diagnose(request)
    output = to_manager(checked, 1)
    assert not output.success and output.error == "CONTEXT_SCOPE_MISMATCH"
    assert scenario.provider.calls == 0


def test_later_worktree_edits_do_not_change_sealed_revision(scenario: Scenario) -> None:
    path = scenario.harness.root / "app.py"
    path.write_text("changed source", encoding="utf-8")
    checked = service(scenario).diagnose(scenario.request)
    output = to_manager(checked, 1)
    assert output.success and output.data["status"] == "completed"
    assert 'return profile["name"]' in output.data["evidence"][0]["excerpt"]
    assert path.read_text(encoding="utf-8") == "changed source"
