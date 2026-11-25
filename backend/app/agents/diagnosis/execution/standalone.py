"""Child-only standalone initialization; no Manager ORM/session assumptions."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from sqlite3 import Connection

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.pool import ConnectionPoolEntry

from app.agents.diagnosis.code_rag.config import RagSettings
from app.agents.diagnosis.code_rag.service import CodeRag
from app.agents.diagnosis.quality.contracts import QualityResult
from app.agents.diagnosis.quality.service import QualityDiagnosisService
from app.agents.diagnosis.reasoning.config import DiagnosisSettings
from app.agents.diagnosis.reasoning.contracts import DiagnosisRequest
from app.core.config import BACKEND_ROOT, DemoWorkspace, Settings
from app.db.session import create_database_engine
from app.schemas.common import WireModel

from .control import ExecutionControl
from .errors import ExecutionFailure


class StandaloneStorage(WireModel):
    """Serializable local references only; never an engine, session or operator secret."""

    database_path: Path
    artifact_root: Path
    demo_root: Path
    permitted_workspaces: dict[str, DemoWorkspace]
    artifact_max_bytes: int


@dataclass(frozen=True)
class StandaloneFactory:
    """Trusted application configuration, never constructed from Manager request fields."""

    storage_json: str
    rag_json: str
    diagnosis_json: str

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        rag: RagSettings | None = None,
        diagnosis: DiagnosisSettings | None = None,
    ) -> "StandaloneFactory":
        database = make_url(settings.database_url).database
        if not database or database == ":memory:":
            raise ValueError("Process execution requires an existing file database")
        path = Path(database)
        path = path if path.is_absolute() else BACKEND_ROOT / path
        storage = StandaloneStorage(
            database_path=path.resolve(),
            artifact_root=settings.artifact_root,
            demo_root=settings.demo_root,
            permitted_workspaces=settings.permitted_workspaces,
            artifact_max_bytes=settings.artifact_max_bytes,
        )
        return cls(
            storage.model_dump_json(),
            (rag or RagSettings()).model_dump_json(),
            (diagnosis or DiagnosisSettings()).model_dump_json(),
        )

    @contextmanager
    def __call__(
        self, control: ExecutionControl, observe: Callable[[ExecutionFailure], None]
    ) -> Iterator[Callable[[DiagnosisRequest], QualityResult]]:
        storage = StandaloneStorage.model_validate_json(self.storage_json)
        if not storage.database_path.is_absolute() or not storage.database_path.is_file():
            raise ValueError("Standalone database is unavailable")
        settings = Settings(
            _env_file=None,
            operator_token=None,
            database_url="sqlite:///" + storage.database_path.as_posix(),
            **storage.model_dump(exclude={"database_path"}),
        )
        engine = create_database_engine(settings)

        @event.listens_for(engine, "connect")
        def read_only(connection: Connection, record: ConnectionPoolEntry) -> None:
            connection.execute("PRAGMA query_only=ON")

        try:
            rag = CodeRag(
                engine, settings, RagSettings.model_validate_json(self.rag_json), control=control
            )
            service = QualityDiagnosisService(
                engine,
                settings,
                rag,
                config=DiagnosisSettings.model_validate_json(self.diagnosis_json),
                control=control,
                failure_observer=observe,
            )
            yield service.diagnose
        finally:
            engine.dispose()
