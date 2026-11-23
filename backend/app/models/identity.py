from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import Digest, UTCDateTime
from app.models.common import Record, constraints, digest_check


class User(Record, Base):
    __tablename__ = "users"
    __table_args__ = constraints(
        CheckConstraint("length(username) BETWEEN 1 AND 128", name="username_length"),
        CheckConstraint(
            "password_hash IS NULL OR length(password_hash) >= 20", name="password_hash"
        ),
    )
    username: Mapped[str] = mapped_column(String(128, collation="NOCASE"), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str | None] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(
        Boolean(create_constraint=True, name="active_bool"), default=True
    )
    roles: Mapped[list["Role"]] = relationship(secondary="user_roles", viewonly=True)
    sessions: Mapped[list["AuthSession"]] = relationship(viewonly=True)


class Role(Record, Base):
    __tablename__ = "roles"
    __table_args__ = constraints(
        CheckConstraint("name IN ('admin','developer','reviewer','viewer')", name="role_name")
    )
    name: Mapped[str] = mapped_column(String(32), unique=True)
    description: Mapped[str] = mapped_column(String(300), default="")
    users: Mapped[list[User]] = relationship(secondary="user_roles", viewonly=True)


class UserRole(Record, Base):
    __tablename__ = "user_roles"
    __table_args__ = constraints(UniqueConstraint("user_id", "role_id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))


class AuthSession(Record, Base):
    __tablename__ = "auth_sessions"
    __table_args__ = constraints(
        digest_check("token_hash"),
        CheckConstraint("expires_at > created_at", name="session_expiry"),
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    token_hash: Mapped[str] = mapped_column(Digest(), unique=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    user: Mapped[User] = relationship(viewonly=True)
