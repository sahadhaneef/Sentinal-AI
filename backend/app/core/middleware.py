from time import perf_counter
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import error_response
from app.core.logging import logger


class RequestContextMiddleware:
    """Pure ASGI middleware, retaining headers and CORS on sanitized failures."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started, sent, status = perf_counter(), False, 500

        async def send_with_headers(message: Message) -> None:
            nonlocal sent, status
            if message["type"] == "http.response.start":
                sent, status = True, message["status"]
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-request-id", request_id.encode("ascii")),
                        (b"x-content-type-options", b"nosniff"),
                        (b"cache-control", b"no-store"),
                    ]
                )
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        except Exception as exc:
            logger.error(
                "request_failed",
                extra={"request_id": request_id, "exception_type": type(exc).__name__},
            )
            if sent:
                raise
            response = error_response(
                request_id, 500, "INTERNAL_ERROR", "The server could not complete this request."
            )
            await response(scope, receive, send_with_headers)
        finally:
            route = getattr(scope.get("route"), "path", "<unmatched>")
            logger.info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "method": scope["method"],
                    "route": route,
                    "status": status,
                    "duration_ms": round((perf_counter() - started) * 1000, 2),
                },
            )
