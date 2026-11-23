"""Database initialization and seed data."""
from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from .models import Application, Base, Setting
from .session import get_engine

DEMO_APP = {
    "id": "app_demo",
    "name": "Registration API",
    "description": "The designated local sample application. A safe workspace for exploring the complete incident lifecycle.",
    "workspace_key": "local_registration_demo",
    "repository_revision": "abc123",
    "monitoring_enabled": True,
    "status": "degraded",
    "supported_errors": json.dumps(["NullReferenceError", "ValidationError"]),
}

DEFAULT_SETTINGS = {
    "monitoring_interval_seconds": "5",
    "max_candidate_revisions": "2",
}


async def init_db() -> None:
    """Create all tables and seed default data."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from .session import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        await _seed(session)
        await session.commit()


async def _seed(session: AsyncSession) -> None:
    from sqlalchemy import select

    # Seed demo application
    existing = await session.scalar(select(Application).where(Application.id == "app_demo"))
    if not existing:
        session.add(Application(**DEMO_APP))

    # Seed default settings
    for key, value in DEFAULT_SETTINGS.items():
        existing_setting = await session.scalar(select(Setting).where(Setting.key == key))
        if not existing_setting:
            session.add(Setting(key=key, value_json=json.dumps(value)))
