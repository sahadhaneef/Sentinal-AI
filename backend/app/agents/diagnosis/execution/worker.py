"""Bounded spawn-per-invocation supervisor; never execute native work on the event loop."""

import asyncio
import math
import multiprocessing
import threading
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic, sleep
from typing import Protocol

from pydantic import Field, model_validator

from app.agents.diagnosis.quality.contracts import QualityResult
from app.agents.diagnosis.quality.manager_adapter import from_manager, validate_result
from app.agents.diagnosis.reasoning.contracts import DiagnosisRequest
from app.schemas.common import WireModel

from .control import CancellationSignal, ExecutionControl, ExecutionStopped
from .errors import ExecutionFailure, FailureKind, classify_review

MAX_MESSAGE_BYTES = 262144
STAGE_TIMEOUT_SECONDS = 120.0


class WorkerFactory(Protocol):
    """Trusted, spawn-picklable initialization hook; receives no parent database handles."""

    def __call__(
        self, control: ExecutionControl, observe: Callable[[ExecutionFailure], None]
    ) -> AbstractContextManager[Callable[[DiagnosisRequest], QualityResult]]: ...


class WorkItem(WireModel):
    request: DiagnosisRequest
    deadline: float = Field(gt=0, allow_inf_nan=False)


class WorkerOutcome(WireModel):
    """Rich internal result; it is not a new Manager/public response envelope."""

    quality: QualityResult | None = None
    failure: ExecutionFailure | None = None
    worker_pid: int | None = None
    termination: str | None = None

    @model_validator(mode="after")
    def has_outcome(self) -> "WorkerOutcome":
        if self.quality is None and self.failure is None:
            raise ValueError("A worker must return a result or a classified failure")
        if self.quality is not None and self.quality.result.status == "completed" and self.failure:
            raise ValueError("A completed diagnosis cannot also be a failed invocation")
        return self


def failed(kind: FailureKind, **metadata: object) -> WorkerOutcome:
    """Create a safe error without raw child exception, log or source content."""
    return WorkerOutcome(failure=ExecutionFailure(kind=kind), **metadata)


def _child_main(
    payload: str, factory: WorkerFactory, signal: CancellationSignal, output: str
) -> None:
    """Top-level spawn target; all models, repositories and connections initialize here."""
    outcome = failed(FailureKind.STARTUP)
    initialized = False
    try:
        item = WorkItem.model_validate_json(payload)
        control = ExecutionControl(item.deadline, signal)
        control.checkpoint("before_initialization")
        observations: list[ExecutionFailure] = []
        with factory(control, observations.append) as diagnose:
            initialized = True
            control.checkpoint("before_context")
            quality = validate_result(diagnose(item.request))
            control.checkpoint("before_return")
            failure = None
            if quality.result.error:
                failure = (
                    observations[-1]
                    if observations and quality.result.error.code == "LLM_UNAVAILABLE"
                    else classify_review(quality.result.error.code)
                )
            outcome = WorkerOutcome(quality=quality, failure=failure)
    except ExecutionStopped as error:
        outcome = failed(
            FailureKind.CANCELLED if error.code == "CANCELLED" else FailureKind.DEADLINE
        )
    except Exception:
        # Child errors never become raw Manager error strings.
        outcome = failed(FailureKind.WORKER if initialized else FailureKind.STARTUP)
    data = outcome.model_dump_json().encode()
    if len(data) > MAX_MESSAGE_BYTES:
        data = failed(FailureKind.WORKER).model_dump_json().encode()
    Path(output).write_bytes(data)


class IsolatedDiagnosisWorker:
    """One controller per event loop; bounded processes, queue and supervisor threads.

    A fresh Windows spawn process avoids long-lived native model/session state.
    Only JSON and a cancellation event cross the execution boundary. A bounded
    result file is read after process exit, avoiding blocking pipe-frame reads.
    """

    def __init__(
        self,
        factory: WorkerFactory,
        *,
        concurrency: int = 1,
        max_pending: int = 4,
        cancellation_grace: float = 0.5,
    ) -> None:
        if not 1 <= concurrency <= 2 or not concurrency <= max_pending <= 16:
            raise ValueError("Configure one or two workers and a bounded pending queue")
        if not math.isfinite(cancellation_grace) or not 0.01 <= cancellation_grace <= 2:
            raise ValueError("Configure a bounded cancellation grace period")
        self.factory = factory
        self.grace = cancellation_grace
        self.max_pending = max_pending
        self._slots = asyncio.Semaphore(concurrency)
        self._calls: set[asyncio.Task[WorkerOutcome]] = set()
        self._closed = False
        self._loop: asyncio.AbstractEventLoop | None = None

    async def __aenter__(self) -> "IsolatedDiagnosisWorker":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Cancel owned invocations and await process reaping before closing."""
        self._closed = True
        calls = list(self._calls)
        for task in calls:
            task.cancel()
        if calls:
            await asyncio.gather(*calls, return_exceptions=True)

    async def diagnose(self, request: DiagnosisRequest, *, deadline: float) -> WorkerOutcome:
        """Honor Manager's absolute monotonic deadline; never schedule an automatic retry."""
        loop = asyncio.get_running_loop()
        if self._loop is not None and self._loop is not loop:
            raise RuntimeError("Use one worker controller per event loop")
        self._loop = loop
        if self._closed:
            return failed(FailureKind.WORKER)
        if len(self._calls) >= self.max_pending:
            return failed(FailureKind.BUSY)
        try:
            item = WorkItem(request=request.model_dump(), deadline=deadline)
            # 120 seconds is a cap, not a fresh retry budget. Manager supplies the same deadline.
            item.deadline = min(item.deadline, monotonic() + STAGE_TIMEOUT_SECONDS)
        except (ValueError, TypeError, AttributeError):
            return failed(FailureKind.INVALID_REQUEST)
        if item.deadline <= monotonic():
            return failed(FailureKind.DEADLINE)
        task = asyncio.create_task(self._run(item))
        self._calls.add(task)
        try:
            return await task
        finally:
            self._calls.discard(task)

    async def _run(self, item: WorkItem) -> WorkerOutcome:
        try:
            await asyncio.wait_for(self._slots.acquire(), max(0, item.deadline - monotonic()))
        except TimeoutError:
            return failed(FailureKind.DEADLINE)
        cancelled = threading.Event()
        supervisor = asyncio.create_task(asyncio.to_thread(self._supervise, item, cancelled))
        try:
            result = await asyncio.shield(supervisor)
            if monotonic() >= item.deadline:
                return failed(
                    FailureKind.DEADLINE,
                    worker_pid=result.worker_pid,
                    termination=result.termination,
                )
            return result
        except asyncio.CancelledError:
            cancelled.set()
            # Repeated cancellation must not detach a worker or release its slot early.
            while not supervisor.done():
                try:
                    await asyncio.shield(supervisor)
                except asyncio.CancelledError:
                    continue
            supervisor.result()
            raise
        except Exception:
            return failed(FailureKind.WORKER)
        finally:
            self._slots.release()

    def _supervise(self, item: WorkItem, cancelled: threading.Event) -> WorkerOutcome:
        process = None
        termination = None
        try:
            context = multiprocessing.get_context("spawn")
            signal = context.Event()
            with TemporaryDirectory(prefix="sentinel-diagnosis-worker-") as directory:
                output = Path(directory) / "result.json"
                process = context.Process(
                    target=_child_main,
                    args=(item.model_dump_json(), self.factory, signal, str(output)),
                    daemon=True,
                )
                try:
                    if cancelled.is_set() or monotonic() >= item.deadline:
                        return failed(FailureKind.DEADLINE)
                    process.start()
                except Exception:
                    return failed(FailureKind.STARTUP)
                stopped: FailureKind | None = None
                while process.is_alive():
                    if cancelled.is_set() or monotonic() >= item.deadline:
                        stopped = (
                            FailureKind.CANCELLED if cancelled.is_set() else FailureKind.DEADLINE
                        )
                        signal.set()
                        process.join(self.grace)
                        termination = "cooperative"
                        if process.is_alive():
                            process.terminate()
                            termination = "terminated"
                            process.join(self.grace)
                        if process.is_alive():
                            process.kill()
                            termination = "killed"
                            process.join(self.grace)
                        break
                    sleep(0.01)
                process.join(0)
                if stopped:
                    return failed(stopped, worker_pid=process.pid, termination=termination)
                if (
                    process.exitcode != 0
                    or not output.is_file()
                    or output.stat().st_size > MAX_MESSAGE_BYTES
                ):
                    return failed(FailureKind.WORKER, worker_pid=process.pid)
                try:
                    result = WorkerOutcome.model_validate_json(output.read_bytes())
                except (ValueError, TypeError):
                    return failed(FailureKind.WORKER, worker_pid=process.pid)
                try:
                    if result.quality is not None:
                        checked = validate_result(result.quality)
                        actual = checked.result
                        expected = item.request
                        if (
                            actual.incident_id,
                            actual.run_id,
                            actual.application_id,
                            actual.input_revision,
                        ) != (
                            expected.incident_id,
                            expected.run_id,
                            expected.application_id,
                            expected.repository_revision,
                        ):
                            raise ValueError("Wrong invocation scope")
                    return result.model_copy(
                        update={"worker_pid": process.pid, "termination": termination}
                    )
                except (ValueError, TypeError, AttributeError):
                    return failed(FailureKind.CITATION, worker_pid=process.pid)
        except Exception:
            return failed(FailureKind.WORKER)
        finally:
            if process is not None:
                if process.pid is not None:
                    if process.is_alive():
                        process.kill()
                    process.join()
                process.close()


async def diagnose_from_manager(
    value: object,
    worker: IsolatedDiagnosisWorker,
    *,
    deadline: float,
) -> WorkerOutcome:
    """Unregistered internal boundary preserving the D4A input shape and full metadata."""
    try:
        request = from_manager(value)
    except (ValueError, TypeError):
        return failed(FailureKind.INVALID_REQUEST)
    return await worker.diagnose(request, deadline=deadline)
