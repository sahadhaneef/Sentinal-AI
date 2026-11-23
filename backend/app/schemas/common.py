from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Meta(WireModel):
    request_id: str
    schema_version: Literal["1.0"] = "1.0"


class Envelope[T](WireModel):
    data: T
    meta: Meta


class ErrorBody(WireModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(WireModel):
    error: ErrorBody
    meta: Meta
