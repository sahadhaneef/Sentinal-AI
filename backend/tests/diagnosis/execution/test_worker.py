"""Actual Windows spawn processes, cooperative checkpoints and bounded forced termination."""

import asyncio
import hashlib
import multiprocessing
from pathlib import Path
from time import monotonic

import pytest
from sqlalchemy import func, select

from app.agents.diagnosis.execution import worker as module
from app.agents.diagnosis.execution.errors import FailureKind
from app.agents.diagnosis.execution.standalone import StandaloneFactory
from app.agents.diagnosis.execution.worker import (
    IsolatedDiagnosisWorker,
    diagnose_from_manager,
    failed,
)
from app.agents.diagnosis.quality.manager_adapter import to_manager
from app.models import AuditEvent, Diagnosis, WorkflowRun
from app.repositories.unit_of_work import transaction
from tests.diagnosis.execution.helpers import FixtureFactory, malformed_child
from tests.diagnosis.reasoning.conftest import Scenario


async def entered(marker: Path) -> None:
    end = monotonic() + 10
    while not marker.exists():
        assert monotonic() < end, "Worker did not reach the expected boundary"
        await asyncio.sleep(0.02)


def assert_reaped(pid: int) -> None:
    assert pid not in {process.pid for process in multiprocessing.active_children()}


@pytest.mark.asyncio
async def test_process_preserves_complete_result_and_no_workflow_writes(
    scenario: Scenario, tmp_path: Path
) -> None:
    source = scenario.harness.root / "app.py"
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    with transaction(scenario.harness.engine) as store:
        counts = [
            store.session.scalar(select(func.count()).select_from(model))
            for model in (Diagnosis, AuditEvent, WorkflowRun)
        ]
    factory = FixtureFactory.for_scenario(scenario, tmp_path / "started")
    async with IsolatedDiagnosisWorker(factory) as worker:
        result = await worker.diagnose(scenario.request, deadline=monotonic() + 15)
    assert result.failure is None and result.quality.result.status == "completed"
    assert result.quality.result.hypotheses and result.quality.result.facts
    assert result.quality.provenance.citations[0].content_hash.startswith("sha256:")
    assert to_manager(result.quality, 1).success
    assert_reaped(result.worker_pid)
    assert (tmp_path / "started.closed").is_file()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    with transaction(scenario.harness.engine) as store:
        assert counts == [
            store.session.scalar(select(func.count()).select_from(model))
            for model in (Diagnosis, AuditEvent, WorkflowRun)
        ]


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["retrieval", "reasoning", "noncooperative"])
async def test_cancellation_reaps_workers(scenario: Scenario, tmp_path: Path, phase: str) -> None:
    marker = tmp_path / "started"
    async with IsolatedDiagnosisWorker(
        FixtureFactory.for_scenario(scenario, marker, phase), cancellation_grace=0.2
    ) as worker:
        task = asyncio.create_task(worker.diagnose(scenario.request, deadline=monotonic() + 15))
        await entered(marker)
        pid = int(marker.read_text().split(":")[0])
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert_reaped(pid)
    if phase != "noncooperative":
        assert marker.with_suffix(".closed").is_file()


@pytest.mark.asyncio
async def test_deadline_forces_termination_and_rejects_late_result(
    scenario: Scenario, tmp_path: Path
) -> None:
    async with IsolatedDiagnosisWorker(
        FixtureFactory.for_scenario(scenario, tmp_path / "start", "noncooperative"),
        cancellation_grace=0.1,
    ) as worker:
        result = await worker.diagnose(scenario.request, deadline=monotonic() + 3)
    assert result.quality is None and result.failure.kind == FailureKind.DEADLINE
    assert not result.failure.retry_eligible
    assert result.termination in {"terminated", "killed"}
    assert_reaped(result.worker_pid)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["startup", "crash", "wrong_scope"])
async def test_startup_crash_and_scope_fail_closed(
    scenario: Scenario, tmp_path: Path, mode: str
) -> None:
    async with IsolatedDiagnosisWorker(
        FixtureFactory.for_scenario(scenario, tmp_path / "m", mode)
    ) as worker:
        result = await worker.diagnose(scenario.request, deadline=monotonic() + 15)
    assert result.quality is None and not result.failure.retry_eligible
    assert result.failure.kind in {FailureKind.STARTUP, FailureKind.WORKER, FailureKind.CITATION}
    assert_reaped(result.worker_pid)


@pytest.mark.asyncio
async def test_malformed_child_response_rejected(
    scenario: Scenario, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "_child_main", malformed_child)
    async with IsolatedDiagnosisWorker(
        FixtureFactory.for_scenario(scenario, tmp_path / "m")
    ) as worker:
        result = await worker.diagnose(scenario.request, deadline=monotonic() + 15)
    assert result.quality is None and not result.failure.retry_eligible
    assert result.failure.kind == FailureKind.WORKER
    assert_reaped(result.worker_pid)


@pytest.mark.asyncio
async def test_transient_metadata_survives_without_changing_manager_wire(
    scenario: Scenario, tmp_path: Path
) -> None:
    factory = FixtureFactory.for_scenario(scenario, tmp_path / "m", "transient")
    async with IsolatedDiagnosisWorker(factory) as worker:
        result = await worker.diagnose(scenario.request, deadline=monotonic() + 15)
    assert result.failure.kind == FailureKind.NETWORK and result.failure.retry_eligible
    assert result.quality.result.status == "manual_review"
    wire = to_manager(result.quality, 0)
    assert not wire.success and wire.error == "LLM_UNAVAILABLE"
    assert set(wire.model_dump()) == {"success", "data", "error", "duration_ms"}


@pytest.mark.asyncio
async def test_event_loop_capacity_and_expired_queue_budget(
    scenario: Scenario, tmp_path: Path
) -> None:
    marker = tmp_path / "start"
    ticks = 0

    async def heartbeat() -> None:
        nonlocal ticks
        while True:
            ticks += 1
            await asyncio.sleep(0.01)

    async with IsolatedDiagnosisWorker(
        FixtureFactory.for_scenario(scenario, marker, "reasoning"),
        max_pending=2,
        cancellation_grace=0.1,
    ) as worker:
        beat = asyncio.create_task(heartbeat())
        first = asyncio.create_task(worker.diagnose(scenario.request, deadline=monotonic() + 15))
        await entered(marker)
        second = asyncio.create_task(worker.diagnose(scenario.request, deadline=monotonic() + 0.1))
        await asyncio.sleep(0)
        busy = await worker.diagnose(scenario.request, deadline=monotonic() + 1)
        assert busy.failure.kind == FailureKind.BUSY
        expired = await second
        assert expired.failure.kind == FailureKind.DEADLINE and expired.worker_pid is None
        assert ticks > 2
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        beat.cancel()
        with pytest.raises(asyncio.CancelledError):
            await beat


@pytest.mark.asyncio
async def test_close_cancels_active_invocation(scenario: Scenario, tmp_path: Path) -> None:
    marker = tmp_path / "m"
    worker = IsolatedDiagnosisWorker(FixtureFactory.for_scenario(scenario, marker, "reasoning"))
    task = asyncio.create_task(worker.diagnose(scenario.request, deadline=monotonic() + 15))
    await entered(marker)
    await worker.aclose()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert_reaped(int(marker.read_text().split(":")[0]))


@pytest.mark.asyncio
async def test_standalone_factory_and_invalid_manager_input(scenario: Scenario) -> None:
    factory = StandaloneFactory.from_settings(scenario.harness.settings, scenario.harness.rag)
    assert "operator_token" not in factory.storage_json
    async with IsolatedDiagnosisWorker(factory) as worker:
        invalid = await diagnose_from_manager({}, worker, deadline=monotonic() + 1)
        assert invalid.failure.kind == FailureKind.INVALID_REQUEST and invalid.worker_pid is None
        result = await worker.diagnose(scenario.request, deadline=monotonic() + 15)
    # This test index uses an intentionally synthetic 8D encoder, not production BGE.
    assert result.quality.result.status == "manual_review"
    assert not result.failure.retry_eligible


@pytest.mark.asyncio
@pytest.mark.parametrize("deadline", [float("inf"), float("nan"), -1.0, 0.0])
async def test_invalid_deadlines_never_start_a_process(
    scenario: Scenario, tmp_path: Path, deadline: float
) -> None:
    async with IsolatedDiagnosisWorker(
        FixtureFactory.for_scenario(scenario, tmp_path / "m")
    ) as worker:
        result = await worker.diagnose(scenario.request, deadline=deadline)
    assert result.failure.kind == FailureKind.INVALID_REQUEST and result.worker_pid is None


@pytest.mark.asyncio
async def test_spawn_initialization_failure_is_sanitized(scenario: Scenario) -> None:
    # A local lambda cannot be pickled by Windows spawn; no production hook selects it.
    async with IsolatedDiagnosisWorker(lambda control, observe: None) as worker:
        result = await worker.diagnose(scenario.request, deadline=monotonic() + 5)
    assert result.failure.kind == FailureKind.STARTUP and result.quality is None


@pytest.mark.asyncio
async def test_parent_rejects_late_results_after_supervisor_return(
    scenario: Scenario, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import time

    from tests.diagnosis.quality.test_quality import service

    checked = service(scenario).diagnose(scenario.request)

    def late(item: module.WorkItem, cancelled: object) -> module.WorkerOutcome:
        while monotonic() <= item.deadline:
            time.sleep(0.01)
        return module.WorkerOutcome(quality=checked)

    async with IsolatedDiagnosisWorker(
        FixtureFactory.for_scenario(scenario, tmp_path / "m")
    ) as worker:
        monkeypatch.setattr(worker, "_supervise", late)
        result = await worker.diagnose(scenario.request, deadline=monotonic() + 0.05)
    assert result.quality is None and result.failure.kind == FailureKind.DEADLINE


@pytest.mark.asyncio
async def test_stage_cap_is_120_seconds_without_automatic_retry(
    scenario: Scenario, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[float] = []

    def inspect(item: module.WorkItem, cancelled: object) -> module.WorkerOutcome:
        calls.append(item.deadline)
        return failed(FailureKind.NETWORK)

    start = monotonic()
    async with IsolatedDiagnosisWorker(
        FixtureFactory.for_scenario(scenario, tmp_path / "m")
    ) as worker:
        monkeypatch.setattr(worker, "_supervise", inspect)
        result = await worker.diagnose(scenario.request, deadline=start + 1000)
    assert len(calls) == 1 and start + 119 <= calls[0] <= start + 120.1
    assert result.failure.retry_eligible


@pytest.mark.asyncio
async def test_repeated_cancellation_still_reaps_native_worker(
    scenario: Scenario, tmp_path: Path
) -> None:
    marker = tmp_path / "m"
    factory = FixtureFactory.for_scenario(scenario, marker, "noncooperative")
    async with IsolatedDiagnosisWorker(factory, cancellation_grace=0.2) as worker:
        task = asyncio.create_task(worker.diagnose(scenario.request, deadline=monotonic() + 15))
        await entered(marker)
        task.cancel()
        await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert_reaped(int(marker.read_text().split(":")[0]))
