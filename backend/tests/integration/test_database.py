from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from alembic import command
from app.core.config import BACKEND_ROOT, Settings
from app.main import create_app


def test_migration_upgrade_downgrade_and_reapply_are_real(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    monkeypatch.setenv("SENTINEL_DATABASE_URL", url)
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    # Preserve the original Phase 1 baseline acceptance test. Phase 2 head is
    # independently tested with populated domain records in test_domain_migrations.
    command.upgrade(config, "0001_foundation")
    settings = Settings(_env_file=None, environment="test", database_url=url)
    with TestClient(create_app(settings)) as client:
        engine = client.app.state.engine
        assert inspect(engine).get_table_names() == ["alembic_version"]
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version"))
                == "0001_foundation"
            )
            assert connection.scalar(text("PRAGMA foreign_keys")) == 1
    command.downgrade(config, "base")
    command.upgrade(config, "0001_foundation")


def test_database_connection_lifecycle_survives_restart_without_claiming_domain_persistence(
    tmp_path,
):
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=f"sqlite:///{(tmp_path / 'restart.db').as_posix()}",
    )
    for _ in range(2):
        with TestClient(create_app(settings)) as client:
            assert client.get("/api/v1/health").status_code == 200
            assert inspect(client.app.state.engine).get_table_names() == []
