from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from app.repositories.errors import PersistenceError
from app.schemas.common import ErrorBody, ErrorEnvelope, Meta


class ApiError(Exception):
    """Explicit sanitized HTTP failure shared by routes and application services."""

    def __init__(
        self, status: int, code: str, message: str, details: dict[str, Any] | None = None
    ) -> None:
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}


def error_response(
    request_id: str,
    status: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    envelope = ErrorEnvelope(
        error=ErrorBody(code=code, message=message, details=details or {}),
        meta=Meta(request_id=request_id),
    )
    return JSONResponse(
        status_code=status, content=envelope.model_dump(mode="json"), headers=headers
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(PersistenceError)
    async def persistence_error(request: Request, exc: PersistenceError) -> JSONResponse:
        statuses = {
            "NOT_FOUND": 404,
            "CONFLICT": 409,
            "VALIDATION_ERROR": 422,
            "IMMUTABLE_RECORD": 409,
            "STORAGE_UNAVAILABLE": 503,
        }
        return error_response(
            request.state.request_id, statuses.get(exc.code, 500), exc.code, str(exc)
        )

    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError) -> JSONResponse:
        return error_response(
            request.state.request_id, exc.status, exc.code, exc.message, exc.details
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        codes = {
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            401: "UNAUTHENTICATED",
            403: "FORBIDDEN",
        }
        messages = {
            404: "This resource is not available.",
            405: "This method is not allowed.",
            401: "Authentication is required.",
            403: "This request is not permitted.",
        }
        return error_response(
            request.state.request_id,
            exc.status_code,
            codes.get(exc.status_code, "HTTP_ERROR"),
            messages.get(exc.status_code, "The request could not be completed."),
            headers=dict(exc.headers or {}),
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Never return input values, arbitrary validator messages or exception contexts.
        fields = [{"location": list(error["loc"]), "type": error["type"]} for error in exc.errors()]
        return error_response(
            request.state.request_id,
            422,
            "VALIDATION_ERROR",
            "Check the supplied values and retry.",
            {"fields": fields},
        )
