from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.types import UTCDateTime, utc_now


class Record:
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    schema_version: Mapped[str] = mapped_column(String(8), default="1.0", server_default="1.0")
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utc_now, onupdate=utc_now, server_default=func.current_timestamp()
    )


def constraints(*items):
    return (
        CheckConstraint("length(id) BETWEEN 1 AND 64", name="id_length"),
        CheckConstraint("schema_version = '1.0'", name="schema_version"),
        *items,
    )


def digest_check(column: str) -> CheckConstraint:
    return CheckConstraint(
        f"length({column}) = 71 AND substr({column},1,7) = 'sha256:' "
        f"AND substr({column},8) NOT GLOB '*[^0-9a-f]*'",
        name=f"{column}_format",
    )


def relative_check(column: str) -> CheckConstraint:
    return CheckConstraint(
        f"length({column}) BETWEEN 1 AND 512 AND substr({column},1,1) NOT IN ('/','.') "
        f"AND {column} NOT GLOB '*[^A-Za-z0-9_./-]*' AND instr({column},'..') = 0 "
        f"AND instr({column},'//') = 0",
        name=f"{column}_relative",
    )
