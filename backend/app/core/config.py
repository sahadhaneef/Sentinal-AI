"""Sentinel AI Backend ? Core Configuration."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = (BASE_DIR / "sentinel.db").as_posix()
WORKSPACE_PATH = (BASE_DIR / "demo_app" / "workspace").as_posix()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    app_env: str = "development"
    secret_key: str = "dev-secret-change-in-production-32chars"
    session_max_age_seconds: int = 86400
    cors_allow_origin: str = "http://localhost:5173"

    database_url: str = f"sqlite+aiosqlite:///{DB_PATH}"

    demo_app_id: str = "app_demo"
    demo_workspace_path: str = WORKSPACE_PATH

    llm_provider: str = "stub"

    agent_timeout_seconds: int = 120
    max_candidate_revisions: int = 2
    monitoring_interval_seconds: int = 5

    log_level: str = "INFO"
    log_format: str = "json"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
