import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app import __version__
from app.api.routes.domain import router as domain_router
from app.api.routes.health import router as health_router
from app.core.config import Settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging, logger
from app.core.middleware import RequestContextMiddleware
from app.db.session import create_database_engine
from app.schemas.common import ErrorEnvelope


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an injectable local REST API without migrating or seeding a database."""
    settings = settings if settings is not None else Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.log_level)
        engine = create_database_engine(settings)
        app.state.engine = engine
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("foundation_started")
            yield
        finally:
            engine.dispose()
            logger.info("foundation_stopped")

    app = FastAPI(
        title="SENTINEL AI — local prototype API",
        version=__version__,
        lifespan=lifespan,
        description=(
            "Database-backed read APIs and operator intake. No agents or workflow execution."
        ),
        docs_url="/api/v1/docs",
        redoc_url=None,
        openapi_url="/api/v1/openapi.json",
        responses={code: {"model": ErrorEnvelope} for code in (404, 405, 422, 500)},
    )
    app.state.settings = settings
    app.state.cursor_key = secrets.token_bytes(32)
    register_error_handlers(app)
    app.add_middleware(RequestContextMiddleware)
    # CORS wraps request/error handling so sanitized 500 responses retain CORS headers.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "X-CSRF-Token", "Idempotency-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(domain_router, prefix="/api/v1")
    return app
