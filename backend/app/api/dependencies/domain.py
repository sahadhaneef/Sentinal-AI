"""Request-scoped transactions/services and explicit operator authentication."""

import hmac
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, Request

from app.core.errors import ApiError
from app.repositories import Store, transaction
from app.services.cursors import CursorCodec
from app.services.intake import IntakeService
from app.services.reads import ReadService


def get_store(request: Request) -> Iterator[Store]:
    """Commit intake only after the response model has been built successfully."""
    with transaction(request.app.state.engine) as store:
        yield store


def read_service(
    request: Request, store: Annotated[Store, Depends(get_store, scope="function")]
) -> ReadService:
    """Inject one service and transaction per request."""
    return ReadService(store, request.app.state.settings, CursorCodec(request.app.state.cursor_key))


def intake_service(
    request: Request, store: Annotated[Store, Depends(get_store, scope="function")]
) -> IntakeService:
    return IntakeService(store, request.app.state.settings)


def require_operator(
    request: Request, authorization: Annotated[str | None, Header()] = None
) -> None:
    """Bearer authority is server-configured, never derived from JSON or a cookie."""
    configured = request.app.state.settings.operator_token
    if configured is None:
        raise ApiError(403, "FORBIDDEN", "Operator intake is disabled until a token is configured.")
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError(401, "UNAUTHENTICATED", "An operator bearer token is required.")
    if not hmac.compare_digest(authorization[7:].encode(), configured.get_secret_value().encode()):
        raise ApiError(403, "FORBIDDEN", "This operator token is not permitted.")
    if request.headers.get("origin"):
        # No browser operator-token flow is implemented; prevents ambient browser writes.
        raise ApiError(403, "FORBIDDEN", "Use the local operator client for intake.")


ReadDependency = Annotated[ReadService, Depends(read_service)]
IntakeDependency = Annotated[IntakeService, Depends(intake_service)]
