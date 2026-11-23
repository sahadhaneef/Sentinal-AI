"""Normalized observation handoff shared by repositories and HTTP intake."""

from datetime import UTC
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.db.types import Digest, validate_token
from app.models.enums import Severity


class MonitoringInput(BaseModel):
    """Already-normalized, sanitized input from a future service, not a log parser."""

    model_config = ConfigDict(extra="forbid")
    application_id: str
    repository_revision: str
    source_event_id: str = Field(min_length=1, max_length=256)
    fingerprint: str
    severity: Severity
    error_type: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=2000)
    classification: Literal["supported", "unsupported"] = "supported"
    log_artifact_id: str | None = None
    occurred_at: AwareDatetime

    @field_validator("application_id", "repository_revision")
    @classmethod
    def validate_identifiers(cls, value: str) -> str:
        return validate_token(value)

    @field_validator("fingerprint")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        return Digest().process_bind_param(value, None)

    @field_validator("occurred_at")
    @classmethod
    def normalize_time(cls, value: AwareDatetime) -> AwareDatetime:
        return value.astimezone(UTC)
