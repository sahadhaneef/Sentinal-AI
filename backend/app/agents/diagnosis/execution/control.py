"""Cooperative checkpoints supplement, rather than replace, process supervision."""

from dataclasses import dataclass
from time import monotonic
from typing import Protocol


class CancellationSignal(Protocol):
    """Only the event operation needed inside synchronous Diagnosis code."""

    def is_set(self) -> bool: ...


class ExecutionStopped(BaseException):
    """Control flow that broad provider/retrieval exception handlers must not swallow."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ExecutionControl:
    """Use the parent's system monotonic deadline, including startup and queue time."""

    deadline: float | None = None
    cancellation: CancellationSignal | None = None

    def checkpoint(self, stage: str) -> None:
        """Stop at a named safe boundary; stage names contain no source or log text."""
        if self.cancellation is not None and self.cancellation.is_set():
            raise ExecutionStopped("CANCELLED")
        if self.deadline is not None and monotonic() >= self.deadline:
            raise ExecutionStopped("STAGE_TIMEOUT")

    def timeout(self, configured: float) -> float:
        """Cap a socket operation without extending the execution budget."""
        self.checkpoint("before_network")
        remaining = (
            configured if self.deadline is None else min(configured, self.deadline - monotonic())
        )
        if remaining <= 0:
            raise ExecutionStopped("STAGE_TIMEOUT")
        return remaining
