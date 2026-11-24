"""Opt-in local LLM configuration, independent of the strict shared dotenv schema."""

import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DiagnosisSettings(BaseSettings):
    """Use process SENTINEL_DIAGNOSIS_* variables; never silently download a model."""

    model_config = SettingsConfigDict(
        env_prefix="SENTINEL_DIAGNOSIS_", env_file=None, extra="forbid"
    )
    provider: Literal["disabled", "ollama"] = "disabled"
    model: str = ""
    base_url: str = "http://127.0.0.1:11434"
    timeout_seconds: float = Field(default=30, ge=0.1, le=120, allow_inf_nan=False)
    max_response_bytes: int = Field(default=65536, ge=1024, le=262144)
    allow_test_fallback: bool = False

    @field_validator("base_url")
    @classmethod
    def loopback_only(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "::1"}
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or not parsed.port
        ):
            raise ValueError("Use an explicit loopback HTTP address and port without credentials")
        return value.rstrip("/")

    @model_validator(mode="after")
    def configured_model(self) -> "DiagnosisSettings":
        if self.provider == "ollama" and not re.fullmatch(r"[A-Za-z0-9_./:-]{1,128}", self.model):
            raise ValueError("Configure an already installed local model name")
        if ".." in self.model or "://" in self.model:
            raise ValueError("A model identifier cannot be a URL or traversal path")
        if self.model.endswith("-cloud"):
            raise ValueError("Hosted model tags are not supported by this local adapter")
        return self
