"""Migrated domain database, permitted synthetic source and test-only encoder."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import Engine

from app.agents.diagnosis.code_rag.config import RagSettings
from app.agents.diagnosis.code_rag.service import CodeRag
from app.core.config import DemoWorkspace, Settings
from app.models import Application, Artifact, RepositoryRevision
from app.repositories.unit_of_work import transaction
from tests.database.conftest import database as migrated_database

database = migrated_database


class TestEncoder:
    """Small fixed vocabulary for predictable isolated tests, explicitly non-semantic."""

    __test__ = False
    dimensions = 8
    profile = "TEST-ONLY-vocabulary-v1:8"
    vocabulary = ("profile", "registration", "database", "payment", "email", "cache", "user")

    def __init__(self) -> None:
        self.calls = 0
        self.query_calls = 0
        self.fail = False

    def _vector(self, text: str) -> list[float]:
        words = re.findall(r"[a-z]+", text.lower())
        return [float(words.count(word)) for word in self.vocabulary] + [0.1]

    def documents(self, texts: Sequence[str]) -> list[list[float]]:
        if self.fail:
            raise RuntimeError("private source must never escape provider exceptions")
        self.calls += len(texts)
        return [self._vector(text) for text in texts]

    def query(self, text: str) -> list[float]:
        self.query_calls += 1
        if self.fail:
            raise RuntimeError("private query must never escape")
        return self._vector(text)


@dataclass
class Harness:
    engine: Engine
    settings: Settings
    rag: RagSettings
    root: Path
    encoder: TestEncoder
    service: CodeRag

    def register(self, revision: str, application_id: str = "rag_app", key: str = "sample") -> None:
        """Register only operator-owned synthetic revisions via existing repositories."""
        with transaction(self.engine) as store:
            if store.session.get(Application, application_id) is None:
                store.applications.add(
                    Application(id=application_id, name="RAG fixture", workspace_key=key)
                )
            artifact_id = f"snapshot_{application_id}_{revision}"
            store.records(Artifact).add(
                Artifact(
                    id=artifact_id,
                    kind="source_snapshot",
                    storage_key=f"registered/{artifact_id}",
                    sha256="sha256:" + "a" * 64,
                    size_bytes=0,
                    content_type="application/octet-stream",
                    redacted=False,
                )
            )
            record = store.records(RepositoryRevision).add(
                RepositoryRevision(
                    application_id=application_id,
                    revision=revision,
                    snapshot_artifact_id=artifact_id,
                )
            )
            store.applications.select_revision(application_id, record.id)
        self.settings.permitted_workspaces[key] = DemoWorkspace(
            name="RAG fixture",
            revision=revision,
            snapshot_key=f"registered/{artifact_id}",
        )
        (self.settings.demo_root / key).mkdir(parents=True, exist_ok=True)


@pytest.fixture
def harness(database: Engine, tmp_path: Path) -> Harness:
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=str(database.url),
        artifact_root=tmp_path / "content",
        demo_root=tmp_path / "sources",
    )
    rag = RagSettings(index_root=tmp_path / "index", model_root=tmp_path / "models")
    encoder = TestEncoder()
    value = Harness(
        database,
        settings,
        rag,
        settings.demo_root / "sample",
        encoder,
        CodeRag(database, settings, rag, encoder),
    )
    value.register("r1")
    return value
