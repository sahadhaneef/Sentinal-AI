"""Test fixtures and conftest."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    factory = async_sessionmaker(bind=db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):
    """AsyncClient with in-memory SQLite database override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Seed demo app
    import json

    from app.db.models import Application, Setting
    db_session.add(Application(
        id="app_demo",
        name="Registration API",
        description="Demo app",
        workspace_key="local_registration_demo",
        repository_revision="abc123",
        monitoring_enabled=True,
        status="degraded",
        supported_errors=json.dumps(["NullReferenceError", "ValidationError"]),
    ))
    db_session.add(Setting(key="monitoring_interval_seconds", value_json="5"))
    db_session.add(Setting(key="max_candidate_revisions", value_json="2"))
    await db_session.commit()

    from app.core.security import create_session_token

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        cookies={"sentinel_session": create_session_token("demo_reviewer"), "csrf_token": "test_csrf"},
        headers={"X-CSRF-Token": "test_csrf"},
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
