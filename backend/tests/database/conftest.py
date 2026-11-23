from datetime import UTC, datetime

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import BACKEND_ROOT, Settings
from app.db.session import create_database_engine

NOW = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)
HASH = "sha256:" + "a" * 64
HASH2 = "sha256:" + "b" * 64
FINGERPRINT = "sha256:" + "f" * 64
DOMAIN_TABLES = {
    "users",
    "roles",
    "user_roles",
    "auth_sessions",
    "applications",
    "repository_revisions",
    "application_revisions",
    "artifacts",
    "monitoring_events",
    "incidents",
    "incident_monitoring_events",
    "workflow_runs",
    "stage_transitions",
    "agent_executions",
    "diagnoses",
    "code_index_entries",
    "evidence_references",
    "patch_candidates",
    "validation_results",
    "validation_checks",
    "approval_decisions",
    "application_attempts",
    "verification_results",
    "verification_checks",
    "incident_reports",
    "audit_events",
    "backend_settings",
    "idempotency_records",
}


@pytest.fixture
def database(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'domain.db').as_posix()}"
    monkeypatch.setenv("SENTINEL_DATABASE_URL", url)
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    command.upgrade(config, "head")
    engine = create_database_engine(Settings(_env_file=None, database_url=url, environment="test"))
    yield engine
    engine.dispose()


@pytest.fixture
def minimal(database):
    from tests.database.helpers import seed_minimal

    seed_minimal(database)
    return database


@pytest.fixture
def graph(minimal):
    from tests.database.helpers import seed_graph

    seed_graph(minimal)
    return minimal
