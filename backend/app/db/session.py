from collections.abc import Generator
from pathlib import Path
from sqlite3 import Connection

from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.pool import ConnectionPoolEntry, StaticPool

from app.core.config import BACKEND_ROOT, Settings


def create_database_engine(settings: Settings) -> Engine:
    """Build a local SQLite engine with enforced foreign keys and Unicode search."""
    url = make_url(settings.database_url)
    memory = url.database in (None, "", ":memory:")
    if not memory:
        database = Path(url.database or "")
        database = database if database.is_absolute() else BACKEND_ROOT / database
        database.parent.mkdir(parents=True, exist_ok=True)
        url = url.set(database=str(database.resolve()))
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False, "timeout": 5, "autocommit": False},
        **({"poolclass": StaticPool} if memory else {}),
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection: Connection, _record: ConnectionPoolEntry) -> None:
        previous = connection.autocommit
        connection.create_function(
            "casefold", 1, lambda value: str(value).casefold(), deterministic=True
        )
        connection.autocommit = True
        cursor = connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()
            connection.autocommit = previous

    return engine


def get_session(request: Request) -> Generator[Session, None, None]:
    with Session(request.app.state.engine) as session:
        yield session
