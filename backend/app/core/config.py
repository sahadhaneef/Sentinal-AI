"""Local prototype storage, exact CORS origins and opt-in operator intake settings."""

from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class DemoWorkspace(BaseModel):
    """Operator-owned metadata for one permitted directory under demo_root."""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    revision: str
    snapshot_key: str
    supported_errors: list[str] = Field(default_factory=list, max_length=20)


class Settings(BaseSettings):
    """Validated local-only configuration; operator secrets never enter public DTOs."""

    model_config = SettingsConfigDict(
        env_prefix="SENTINEL_", env_file=BACKEND_ROOT / ".env", extra="forbid"
    )

    environment: Literal["local", "test"] = "local"
    database_url: str = "sqlite:///artifacts/sentinel.db"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    artifact_root: Path = BACKEND_ROOT / "artifacts" / "content"
    demo_root: Path = BACKEND_ROOT / "demo_workspaces"
    permitted_workspaces: dict[str, DemoWorkspace] = Field(default_factory=dict)
    operator_token: SecretStr | None = None
    artifact_max_bytes: int = Field(default=1_048_576, ge=1, le=4_194_304)

    @field_validator("operator_token")
    @classmethod
    def strong_operator_token(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value()) < 32:
            raise ValueError(
                "Use an independently generated operator token of at least 32 characters"
            )
        return value

    @field_validator("artifact_root", "demo_root")
    @classmethod
    def absolute_storage_root(cls, value: Path) -> Path:
        return value if value.is_absolute() else BACKEND_ROOT / value

    @field_validator("permitted_workspaces")
    @classmethod
    def safe_workspaces(cls, value: dict[str, DemoWorkspace]) -> dict[str, DemoWorkspace]:
        from app.db.types import validate_relative_key, validate_token

        for key, workspace in value.items():
            validate_token(key)
            validate_token(workspace.revision)
            validate_relative_key(workspace.snapshot_key)
        return value

    @field_validator("cors_origins")
    @classmethod
    def local_origins_only(cls, origins: list[str]) -> list[str]:
        if not origins:
            raise ValueError("Configure at least one exact local frontend origin")
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
                or "*" in origin
            ):
                raise ValueError("Only exact loopback origins without paths are supported")
            # Accessing port also validates malformed/out-of-range port strings.
            _ = parsed.port
        return list(dict.fromkeys(origins))

    @field_validator("database_url")
    @classmethod
    def sqlite_only(cls, value: str) -> str:
        parsed = make_url(value)
        if parsed.drivername != "sqlite" or parsed.host or parsed.username or parsed.query:
            raise ValueError("Phase 1 supports plain local SQLite URLs only")
        return value
