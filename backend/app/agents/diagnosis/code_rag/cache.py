"""Separate regenerable SQLite vector cache; domain metadata/migrations stay unchanged."""

import hashlib
import struct
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import JSON, Engine, LargeBinary, String, inspect, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.core.config import Settings
from app.db.session import create_database_engine

from .errors import IndexUnavailable, RevisionConflict
from .ingestion import reject_redirects


class CacheBase(DeclarativeBase):
    """Intentionally independent from the main application's Base metadata."""


class Seal(CacheBase):
    __tablename__ = "rag_source_seals_v1"
    scope: Mapped[str] = mapped_column(String, primary_key=True)
    snapshot_hash: Mapped[str] = mapped_column(String)
    manifest_ref: Mapped[str] = mapped_column(String)


class Vector(CacheBase):
    __tablename__ = "rag_vectors_v1"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    dimensions: Mapped[int] = mapped_column()
    data: Mapped[bytes] = mapped_column(LargeBinary)
    checksum: Mapped[str] = mapped_column(String)


class Collection(CacheBase):
    __tablename__ = "rag_collections_v1"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    scope: Mapped[str] = mapped_column(String, index=True)
    snapshot_hash: Mapped[str] = mapped_column(String)
    manifest_ref: Mapped[str] = mapped_column(String)
    members: Mapped[list[dict[str, str]]] = mapped_column(JSON)


class VectorCache:
    """All writes are atomic, rollback on failure, and never create the domain schema."""

    def __init__(self, root: Path) -> None:
        self.root = root

    @contextmanager
    def session(self, create: bool = False) -> Iterator[Session]:
        engine: Engine | None = None
        try:
            reject_redirects(self.root)
            path = self.root / "vectors-v1.sqlite3"
            reject_redirects(path)
            if not create and not path.is_file():
                raise IndexUnavailable("INDEX_UNAVAILABLE", "The scoped index has not been built.")
            if create:
                self.root.mkdir(parents=True, exist_ok=True)
            engine = create_database_engine(
                Settings(_env_file=None, database_url=f"sqlite:///{path.as_posix()}")
            )
            tables = set(inspect(engine).get_table_names())
            expected = set(CacheBase.metadata.tables)
            if tables and tables != expected:
                raise IndexUnavailable("INDEX_SCHEMA", "The private cache schema is incompatible.")
            if create and not tables:
                CacheBase.metadata.create_all(engine)
            with Session(engine, expire_on_commit=False) as session, session.begin():
                yield session
        except SQLAlchemyError:
            raise IndexUnavailable(
                "INDEX_UNAVAILABLE", "The private index is unavailable."
            ) from None
        finally:
            if engine is not None:
                engine.dispose()

    def reserve(self, scope: str, snapshot_hash: str, manifest_ref: str) -> None:
        """Reserve immutable source identity before writing any main database evidence."""
        with self.session(create=True) as session:
            seal = session.get(Seal, scope)
            if seal is None:
                session.add(
                    Seal(scope=scope, snapshot_hash=snapshot_hash, manifest_ref=manifest_ref)
                )
            elif seal.snapshot_hash != snapshot_hash:
                raise RevisionConflict(
                    "REVISION_CHANGED", "Register a new revision for changed or deleted source."
                )

    def vectors(self, keys: list[str], dimensions: int) -> dict[str, list[float]]:
        result = {}
        with self.session() as session:
            for offset in range(0, len(keys), 200):
                rows = session.scalars(
                    select(Vector).where(Vector.key.in_(keys[offset : offset + 200]))
                )
                for row in rows:
                    if (
                        row.dimensions != dimensions
                        or len(row.data) != 4 * dimensions
                        or hashlib.sha256(row.data).hexdigest() != row.checksum
                    ):
                        raise IndexUnavailable(
                            "VECTOR_CORRUPT", "Cached embedding integrity check failed."
                        )
                    result[row.key] = list(struct.unpack(f"<{dimensions}f", row.data))
        return result

    def publish(self, collection: Collection, vectors: dict[str, list[float]]) -> None:
        """Publish only after the referencing domain evidence transaction has committed."""
        with self.session() as session:
            for key, vector in vectors.items():
                if session.get(Vector, key) is None:
                    data = struct.pack(f"<{len(vector)}f", *vector)
                    session.add(
                        Vector(
                            key=key,
                            dimensions=len(vector),
                            data=data,
                            checksum=hashlib.sha256(data).hexdigest(),
                        )
                    )
            existing = session.get(Collection, collection.key)
            if existing is None:
                session.add(collection)
            elif (existing.snapshot_hash, existing.members) != (
                collection.snapshot_hash,
                collection.members,
            ):
                raise RevisionConflict(
                    "COLLECTION_CHANGED", "An immutable index collection conflicts."
                )

    def collection(self, key: str) -> Collection | None:
        with self.session() as session:
            return session.get(Collection, key)
