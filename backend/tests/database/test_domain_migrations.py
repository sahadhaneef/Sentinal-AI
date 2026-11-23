import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from alembic import command
from app.core.config import BACKEND_ROOT, Settings
from app.db.session import create_database_engine
from app.main import create_app
from app.models import User
from app.repositories import transaction
from tests.database.conftest import DOMAIN_TABLES


def configuration(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    monkeypatch.setenv("SENTINEL_DATABASE_URL", url)
    return Config(str(BACKEND_ROOT / "alembic.ini")), Settings(
        _env_file=None, environment="test", database_url=url
    )


def test_upgrade_preserves_existing_data_and_has_no_schema_drift(tmp_path, monkeypatch):
    config, settings = configuration(tmp_path, monkeypatch)
    command.upgrade(config, "0001_foundation")
    engine = create_database_engine(settings)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE legacy_notes (value TEXT NOT NULL)"))
            connection.execute(text("INSERT INTO legacy_notes VALUES ('keep me')"))
        command.upgrade(config, "head")
        assert set(inspect(engine).get_table_names()) == DOMAIN_TABLES | {
            "alembic_version",
            "legacy_notes",
        }
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT value FROM legacy_notes")) == "keep me"
            assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
        command.check(config)
    finally:
        engine.dispose()


def test_empty_downgrade_and_reupgrade(tmp_path, monkeypatch):
    config, settings = configuration(tmp_path, monkeypatch)
    command.upgrade(config, "head")
    command.downgrade(config, "0001_foundation")
    engine = create_database_engine(settings)
    try:
        assert inspect(engine).get_table_names() == ["alembic_version"]
        command.upgrade(config, "head")
        assert set(inspect(engine).get_table_names()) == DOMAIN_TABLES | {"alembic_version"}
        command.check(config)
    finally:
        engine.dispose()


def test_populated_downgrade_is_refused_without_losing_data(tmp_path, monkeypatch):
    config, settings = configuration(tmp_path, monkeypatch)
    command.upgrade(config, "head")
    engine = create_database_engine(settings)
    try:
        with transaction(engine) as store:
            store.users.add(User(id="retained", username="retained", display_name="Retained"))
        with pytest.raises(RuntimeError, match="downgrade refused"):
            command.downgrade(config, "0001_foundation")
        with transaction(engine) as store:
            assert store.users.get("retained").username == "retained"
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version")) == "0002_domain"
            )
        assert set(inspect(engine).get_table_names()) == DOMAIN_TABLES | {"alembic_version"}
    finally:
        engine.dispose()


def test_failed_upgrade_rolls_back_new_ddl_and_preserves_original_table(tmp_path, monkeypatch):
    config, settings = configuration(tmp_path, monkeypatch)
    command.upgrade(config, "0001_foundation")
    engine = create_database_engine(settings)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE workflow_runs (original TEXT)"))
            connection.execute(text("INSERT INTO workflow_runs VALUES ('existing')"))
        with pytest.raises(OperationalError, match="already exists"):
            command.upgrade(config, "head")
        assert set(inspect(engine).get_table_names()) == {"alembic_version", "workflow_runs"}
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT original FROM workflow_runs")) == "existing"
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version"))
                == "0001_foundation"
            )
    finally:
        engine.dispose()


def test_domain_records_survive_engine_and_application_restart(graph):
    url = str(graph.url)
    graph.dispose()
    settings = Settings(_env_file=None, environment="test", database_url=url)
    for _ in range(2):
        with TestClient(create_app(settings)) as client:
            assert client.get("/api/v1/health").status_code == 200
            with transaction(client.app.state.engine) as store:
                assert store.users.get("reviewer").username == "reviewer"
                assert store.patches.get("patch_001").validations[0].status == "passed"
            with client.app.state.engine.connect() as connection:
                assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
