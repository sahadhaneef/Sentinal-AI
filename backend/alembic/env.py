from typing import Any

from sqlalchemy import UniqueConstraint, inspect

from alembic import context
from app import models  # noqa: F401 -- register all tables for autogeneration/check
from app.core.config import Settings
from app.db.base import Base
from app.db.session import create_database_engine
from app.db.types import Digest, FileList, RelativeKey, SmallJSON, Token, UTCDateTime

target_metadata = Base.metadata


def include_object(
    item: Any, name: str | None, kind: str, reflected: bool, compare_to: Any
) -> bool:
    # Autogeneration must never propose deleting tables owned by other tools.
    if kind == "table" and reflected and compare_to is None:
        return False
    if kind == "unique_constraint":
        # Phase 2 generated some duplicate constraint names. SQLite uniqueness is
        # defined by its columns, so compare equivalent definitions rather than
        # Alembic's ambiguous name pairing. Missing/extra column sets remain diffs.
        columns = frozenset(item.columns.keys())
        if reflected:
            target = target_metadata.tables.get(item.table.name)
            return target is None or columns not in {
                frozenset(constraint.columns.keys())
                for constraint in target.constraints
                if isinstance(constraint, UniqueConstraint)
            }
        connection = context.get_context().bind
        existing = inspect(connection).get_unique_constraints(item.table.name)
        return columns not in {frozenset(constraint["column_names"]) for constraint in existing}
    return True


def render_type(kind: str, item: Any, _context: Any) -> str | bool:
    """Freeze physical SQL types in migrations, not mutable application model imports."""
    if kind == "type" and isinstance(
        item, (Digest, FileList, RelativeKey, SmallJSON, Token, UTCDateTime)
    ):
        return f"sa.{item.impl!r}"
    return False


def run_migrations() -> None:
    settings = Settings()
    if context.is_offline_mode():
        context.configure(
            url=settings.database_url,
            target_metadata=target_metadata,
            literal_binds=True,
            render_item=render_type,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()
    else:
        engine = create_database_engine(settings)
        try:
            with engine.connect() as connection:
                context.configure(
                    connection=connection,
                    target_metadata=target_metadata,
                    render_item=render_type,
                    include_object=include_object,
                )
                with context.begin_transaction():
                    context.run_migrations()
        finally:
            engine.dispose()


run_migrations()
