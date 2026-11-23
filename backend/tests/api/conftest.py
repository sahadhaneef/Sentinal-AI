"""Isolated persisted records and real artifact bytes; never production seed data."""

import hashlib
import secrets
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.core.config import DemoWorkspace, Settings
from app.main import create_app
from app.models import Artifact
from app.repositories import transaction
from tests.database import helpers
from tests.database.conftest import database as migrated_database

database = migrated_database

TOKEN = secrets.token_urlsafe(32)
CONTENT = b"--- a/example.py\n+++ b/example.py\n@@ -1 +1 @@\n-old\n+new\n"


@pytest.fixture
def api_settings(database: Engine, tmp_path: Path) -> Settings:
    root = tmp_path / "artifacts"
    root.mkdir()
    demo = tmp_path / "workspaces"
    (demo / "demo").mkdir(parents=True)
    return Settings(
        _env_file=None,
        environment="test",
        database_url=str(database.url),
        artifact_root=root,
        demo_root=demo,
        operator_token=TOKEN,
        permitted_workspaces={
            "demo": DemoWorkspace(
                name="Explicit test fixture",
                revision="demoabc",
                snapshot_key="fixtures/snapshot.txt",
                supported_errors=["KeyError"],
            )
        },
    )


@pytest.fixture
def api_client(api_settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(api_settings)) as client:
        yield client


@pytest.fixture
def populated(database: Engine, api_settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(helpers, "HASH", "sha256:" + hashlib.sha256(CONTENT).hexdigest())
    helpers.seed_minimal(database)
    with transaction(database) as store:
        for artifact in store.records(Artifact).list():
            path = api_settings.artifact_root / artifact.storage_key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(CONTENT)
            artifact.size_bytes = len(CONTENT)
        store.applications.update("app_demo", supported_errors=["KeyError"])
    helpers.seed_graph(database)
