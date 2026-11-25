"""Spawn-importable deterministic test hooks, never selected by production configuration."""

import os
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from app.agents.diagnosis.code_rag.config import RagSettings
from app.agents.diagnosis.code_rag.service import CodeRag
from app.agents.diagnosis.execution.control import CancellationSignal, ExecutionControl
from app.agents.diagnosis.execution.errors import ExecutionFailure, FailureKind
from app.agents.diagnosis.execution.standalone import StandaloneFactory, StandaloneStorage
from app.agents.diagnosis.quality.contracts import QualityResult
from app.agents.diagnosis.quality.service import QualityDiagnosisService
from app.agents.diagnosis.reasoning.contracts import DiagnosisRequest, ReasoningContext
from app.agents.diagnosis.reasoning.providers import ReasoningUnavailable
from app.core.config import Settings
from app.db.session import create_database_engine
from tests.diagnosis.conftest import TestEncoder
from tests.diagnosis.reasoning.conftest import FixtureReasoner, Scenario


@dataclass(frozen=True)
class FixtureFactory:
    configuration: StandaloneFactory
    marker: str
    mode: str = "normal"

    @classmethod
    def for_scenario(
        cls, scenario: Scenario, marker: Path, mode: str = "normal"
    ) -> "FixtureFactory":
        return cls(
            StandaloneFactory.from_settings(scenario.harness.settings, scenario.harness.rag),
            str(marker),
            mode,
        )

    @contextmanager
    def __call__(
        self, control: ExecutionControl, observe: Callable[[ExecutionFailure], None]
    ) -> Iterator[Callable[[DiagnosisRequest], QualityResult]]:
        if self.mode == "startup":
            raise RuntimeError("private initialization detail")
        storage = StandaloneStorage.model_validate_json(self.configuration.storage_json)
        settings = Settings(
            _env_file=None,
            operator_token=None,
            database_url="sqlite:///" + storage.database_path.as_posix(),
            **storage.model_dump(exclude={"database_path"}),
        )
        engine = create_database_engine(settings)
        mode, marker = self.mode, Path(self.marker)

        def pause(stage: str) -> None:
            marker.write_text(str(os.getpid()) + ":" + stage)
            if mode == "crash":
                os._exit(17)
            if mode == "noncooperative":
                time.sleep(30)
            if mode in {"retrieval", "reasoning"}:
                while True:
                    control.checkpoint(stage)
                    time.sleep(0.01)

        class Encoder(TestEncoder):
            def query(self, text: str) -> list[float]:
                if mode == "retrieval":
                    pause("retrieval")
                return super().query(text)

        class Reasoner(FixtureReasoner):
            def reason(self, context: ReasoningContext) -> str:
                pause("reasoning")
                if mode == "transient":
                    raise ReasoningUnavailable("safe provider failure", kind=FailureKind.NETWORK)
                if mode == "slow":
                    time.sleep(0.15)
                return super().reason(context)

        try:
            rag = CodeRag(
                engine,
                settings,
                RagSettings.model_validate_json(self.configuration.rag_json),
                Encoder(),
                control=control,
            )
            service = QualityDiagnosisService(
                engine,
                settings,
                rag,
                provider=Reasoner(),
                control=control,
                failure_observer=observe,
            )

            def diagnose(request: DiagnosisRequest) -> QualityResult:
                value = service.diagnose(request)
                if mode == "wrong_scope":
                    value.result.run_id = "another_run"
                return value

            yield diagnose
        finally:
            engine.dispose()
            marker.with_suffix(".closed").write_text("closed")


def malformed_child(payload: str, factory: object, signal: CancellationSignal, output: str) -> None:
    Path(output).write_bytes(b"not JSON")
