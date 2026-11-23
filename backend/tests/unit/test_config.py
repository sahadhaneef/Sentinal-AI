import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "https://evil.example",
        "http://localhost:5173/path",
        "null",
        "http://user:password@localhost:5173",
        "http://localhost:5173?token=private",
        "http://localhost:*",
        "http://localhost:99999",
    ],
)
def test_cors_rejects_nonlocal_or_non_origin_values(origin):
    with pytest.raises((ValidationError, ValueError)):
        Settings(_env_file=None, cors_origins=[origin])


def test_empty_origins_are_not_a_wildcard():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins=[])


def test_config_reads_prefixed_env_without_including_unrelated_env(monkeypatch):
    monkeypatch.setenv("SENTINEL_LOG_LEVEL", "WARNING")
    monkeypatch.setenv("SENTINEL_CORS_ORIGINS", '["http://127.0.0.1:5184"]')
    config = Settings(_env_file=None)
    assert config.log_level == "WARNING"
    assert config.cors_origins == ["http://127.0.0.1:5184"]


@pytest.mark.parametrize("url", ["postgresql://user:secret@db/name", "sqlite://host/db"])
def test_database_is_local_sqlite_only(url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url=url)


def test_production_environment_is_not_an_unsupported_security_claim():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production")
