"""Run labeled synthetic incidents with injected providers or an explicitly configured live LLM."""

import json
import os
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal

from alembic.config import Config
from pydantic import Field, TypeAdapter, field_validator

from alembic import command
from app.agents.diagnosis.code_rag.config import RagSettings
from app.agents.diagnosis.code_rag.embeddings import EmbeddingProvider, LocalSemanticProvider
from app.agents.diagnosis.code_rag.hashing import canonical, digest
from app.agents.diagnosis.code_rag.service import CodeRag
from app.agents.diagnosis.reasoning.config import DiagnosisSettings
from app.agents.diagnosis.reasoning.contracts import DiagnosisRequest, ReasoningContext
from app.agents.diagnosis.reasoning.providers import OllamaProvider, ReasoningProvider
from app.core.config import BACKEND_ROOT, DemoWorkspace, Settings
from app.db.session import create_database_engine
from app.db.types import utc_now, validate_relative_key, validate_token
from app.models import Application, Artifact, RepositoryRevision, WorkflowRun
from app.models.enums import RunState
from app.repositories.incident import MonitoringInput
from app.repositories.unit_of_work import transaction
from app.schemas.common import WireModel

from .service import QualityDiagnosisService


class LabeledCase(WireModel):
    case_id: str
    file_path: str
    source: str = Field(max_length=8000)
    error_type: str
    message: str
    trace: str
    expected_status: Literal["completed", "manual_review"]
    expected_file: str | None
    hypothesis_terms: list[str]

    @field_validator("file_path")
    @classmethod
    def safe_path(cls, value: str) -> str:
        return validate_relative_key(value)

    @field_validator("case_id")
    @classmethod
    def safe_id(cls, value: str) -> str:
        return validate_token(value, 32)


def load_cases() -> list[LabeledCase]:
    return TypeAdapter(list[LabeledCase]).validate_json(
        (BACKEND_ROOT / "fixtures/diagnosis-quality.json").read_bytes()
    )


class ObservedProvider:
    """Count actual invocations, keeping outcome labels out of the model context."""

    def __init__(self, provider: ReasoningProvider) -> None:
        self.provider, self.name = provider, provider.name
        self.calls = 0

    def reason(self, context: ReasoningContext) -> str:
        self.calls += 1
        return self.provider.reason(context)


def evaluate(
    root: Path,
    embedder: EmbeddingProvider,
    provider: ReasoningProvider,
    config: DiagnosisSettings | None = None,
) -> dict[str, Any]:
    """Migrate disposable storage, never touch the real DB, never execute fixture source."""
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=f"sqlite:///{(root / 'evaluation.db').as_posix()}",
        demo_root=root / "sources",
        artifact_root=root / "artifacts",
    )
    previous = os.environ.get("SENTINEL_DATABASE_URL")
    try:
        os.environ["SENTINEL_DATABASE_URL"] = settings.database_url
        command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")
    finally:
        if previous is None:
            os.environ.pop("SENTINEL_DATABASE_URL", None)
        else:
            os.environ["SENTINEL_DATABASE_URL"] = previous
    engine = create_database_engine(settings)
    rag = CodeRag(engine, settings, RagSettings(index_root=root / "index"), embedder)
    observed = ObservedProvider(provider)
    records = []
    try:
        for case in load_cases():
            app_id, revision = f"quality_{case.case_id}", "fixture-v1"
            directory = settings.demo_root / case.case_id
            target = directory / case.file_path
            target.parent.mkdir(parents=True)
            target.write_bytes(case.source.encode())
            source_hash = digest(target.read_bytes())
            snapshot = canonical({"file_path": case.file_path, "hash": source_hash})
            log = case.trace.encode()
            with transaction(engine) as store:
                for suffix, kind, data in [
                    ("snapshot", "source_snapshot", snapshot),
                    ("log", "log", log),
                ]:
                    artifact_id = f"{case.case_id}_{suffix}"
                    key = f"fixtures/{artifact_id}"
                    path = settings.artifact_root / key
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                    store.records(Artifact).add(
                        Artifact(
                            id=artifact_id,
                            kind=kind,
                            storage_key=key,
                            sha256=digest(data),
                            size_bytes=len(data),
                            content_type="text/plain",
                            redacted=kind == "log",
                        )
                    )
                store.applications.add(
                    Application(id=app_id, name=case.case_id, workspace_key=case.case_id)
                )
                registered = store.records(RepositoryRevision).add(
                    RepositoryRevision(
                        application_id=app_id,
                        revision=revision,
                        snapshot_artifact_id=f"{case.case_id}_snapshot",
                    )
                )
                store.applications.select_revision(app_id, registered.id)
                _, incident = store.incidents.record_monitoring_event(
                    MonitoringInput(
                        application_id=app_id,
                        repository_revision=revision,
                        source_event_id=case.case_id,
                        fingerprint=digest(case.case_id.encode()),
                        severity="high",
                        error_type=case.error_type,
                        message=case.message,
                        occurred_at=utc_now(),
                        log_artifact_id=f"{case.case_id}_log",
                    )
                )
                run = store.records(WorkflowRun).add(
                    WorkflowRun(
                        incident_id=incident.id,
                        application_id=app_id,
                        repository_revision=revision,
                        state=RunState.DIAGNOSING,
                    )
                )
            settings.permitted_workspaces[case.case_id] = DemoWorkspace(
                name=case.case_id,
                revision=revision,
                snapshot_key=f"fixtures/{case.case_id}_snapshot",
            )
            rag.index(app_id, revision)
            service = QualityDiagnosisService(
                engine, settings, rag, config=config, provider=observed
            )
            before_calls, started = observed.calls, time.monotonic()
            checked = service.diagnose(
                DiagnosisRequest(
                    incident_id=incident.id,
                    run_id=run.id,
                    application_id=app_id,
                    repository_revision=revision,
                )
            )
            result = checked.result
            text = " ".join(item.statement for item in result.hypotheses).lower()
            records.append(
                {
                    "case_id": case.case_id,
                    "expected_status": case.expected_status,
                    "observed_status": result.status,
                    "status_matches_label": result.status == case.expected_status,
                    "quality_codes": [issue.code for issue in checked.assessment.issues],
                    "error_code": result.error.code if result.error else None,
                    "retrieved_files": [item.file_path for item in checked.provenance.citations],
                    "expected_file_retrieved": case.expected_file
                    in [item.file_path for item in checked.provenance.citations]
                    if case.expected_file
                    else None,
                    "hypothesis_terms_present": all(term in text for term in case.hypothesis_terms)
                    if case.hypothesis_terms
                    else None,
                    "provider_calls": observed.calls - before_calls,
                    "source_unchanged": digest(target.read_bytes()) == source_hash,
                    "elapsed_ms": round((time.monotonic() - started) * 1000),
                    "diagnosis": result.model_dump(mode="json"),
                }
            )
        return {
            "provider": observed.name,
            "embedding_profile": embedder.profile,
            "cases": records,
            "provider_calls": observed.calls,
            "interpretation": "Per-case observations; lexical terms do not prove causal accuracy.",
        }
    finally:
        engine.dispose()


def main() -> None:
    """Explicit live-only path; no deterministic provider is available in this command."""
    config = DiagnosisSettings()
    if config.provider != "ollama" or not config.model or config.allow_test_fallback:
        print(json.dumps({"status": "blocked", "reason": "CONFIGURE_LOCAL_OLLAMA_MODEL"}))
        raise SystemExit(2)
    provider = OllamaProvider(config)
    try:
        with provider.opener.open(config.base_url + "/api/tags", timeout=2) as response:
            tags = json.loads(response.read(65536))
        if config.model not in [item["name"] for item in tags["models"]]:
            raise ValueError("Configured model is not installed")
    except (OSError, ValueError, KeyError):
        print(json.dumps({"status": "blocked", "reason": "LOCAL_MODEL_UNAVAILABLE"}))
        raise SystemExit(2) from None
    with TemporaryDirectory(prefix="sentinel-quality-live-") as temporary:
        report = evaluate(
            Path(temporary), LocalSemanticProvider(RagSettings().model_root), provider, config
        )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
