"""FastAPI main application."""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import get_settings
from .core.errors import SentinelError
from .core.logging import configure_logging, get_logger, new_request_id
from .core.security import _CSRF_COOKIE, _SESSION_COOKIE, create_csrf_token, create_session_token
from .db.base import init_db
from .schemas.common import ApiErrorBody, ApiErrorResponse, Meta

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SENTINEL AI backend starting...")
    await init_db()
    logger.info("Database initialised.")

    # Automatically recover and resume interrupted workflows from DB
    from .db.session import get_session_factory
    from .services.manager import ManagerAgent
    factory = get_session_factory()
    async with factory() as session:
        manager = ManagerAgent(session)
        resumed = await manager.resume_interrupted_workflows()
        if resumed:
            logger.info("Resumed interrupted workflows on startup", extra={"count": len(resumed), "items": resumed})

    yield
    logger.info("SENTINEL AI backend shutting down.")


settings = get_settings()

app = FastAPI(
    title="SENTINEL AI Backend",
    version="1.0.0",
    description="Manager Agent, workflow orchestration, approval and persistence layer.",
    lifespan=lifespan,
)

# ?? CORS ??????????????????????????????????????????????????????????????????????
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_allow_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# ?? Request ID middleware ?????????????????????????????????????????????????????
@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request_id = new_request_id()
    request.state.request_id = request_id
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ?? Session auto-issue (prototype) ????????????????????????????????????????????
@app.middleware("http")
async def auto_session(request: Request, call_next):
    response: Response = await call_next(request)
    if _SESSION_COOKIE not in request.cookies:
        token = create_session_token()
        csrf = create_csrf_token()
        response.set_cookie(
            _SESSION_COOKIE,
            token,
            max_age=settings.session_max_age_seconds,
            httponly=True,
            samesite="lax",
        )
        response.set_cookie(
            _CSRF_COOKIE,
            csrf,
            max_age=settings.session_max_age_seconds,
            httponly=False,  # JS needs to read this
            samesite="lax",
        )
    return response


# ?? Global exception handler ??????????????????????????????????????????????????
@app.exception_handler(SentinelError)
async def sentinel_error_handler(request: Request, exc: SentinelError):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=exc.status,
        content=ApiErrorResponse(
            error=ApiErrorBody(code=exc.code, message=exc.message, details=exc.details),
            meta=Meta(request_id=request_id),
        ).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.exception("Unhandled error", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=ApiErrorResponse(
            error=ApiErrorBody(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred.",
            ),
            meta=Meta(request_id=request_id),
        ).model_dump(mode="json"),
    )


# ?? Routers ???????????????????????????????????????????????????????????????????
from .api.v1 import router as api_v1_router  # noqa: E402

app.include_router(api_v1_router, prefix="/api/v1")
