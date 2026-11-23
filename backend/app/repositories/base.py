from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.types import validate_token
from app.repositories.errors import ImmutableRecord, InvalidRecord, NotFound

MUTABLE_FIELDS = {
    "users": {"display_name", "password_hash", "is_active"},
    "roles": {"description"},
    "auth_sessions": {"revoked_at"},
    "applications": {"name", "description", "status", "monitoring_enabled", "supported_errors"},
    "repository_revisions": {"indexed_at"},
    "incidents": {"status", "current_stage", "resolved_at"},
    "workflow_runs": {"state", "finished_at", "error_artifact_id"},
    "agent_executions": {
        "status",
        "completed_at",
        "duration_ms",
        "output_artifact_id",
        "error_artifact_id",
    },
    "patch_candidates": {"status"},
    "application_attempts": {"status", "after_revision", "restore_status"},
    "backend_settings": {"monitoring_interval_seconds", "max_candidate_revisions"},
    "idempotency_records": {"status", "response_artifact_id"},
}
DELETABLE = {"users", "roles", "user_roles", "auth_sessions", "applications"}


class Repository[T: Base]:
    def __init__(self, session: Session, model: type[T]):
        self.session = session
        self.model = model

    def add(self, record: T) -> T:
        if not isinstance(record, self.model):
            raise InvalidRecord("Record type does not match this repository.")
        self.session.add(record)
        self.session.flush()
        return record

    def get(self, identity: str) -> T:
        try:
            validate_token(identity, 64)
        except ValueError:
            raise InvalidRecord("Invalid record identifier.") from None
        record = self.session.get(self.model, identity)
        if record is None:
            raise NotFound("The record does not exist.")
        return record

    def list(self, *, limit: int = 100, offset: int = 0) -> list[T]:
        if type(limit) is not int or type(offset) is not int or not 1 <= limit <= 100 or offset < 0:
            raise InvalidRecord("Invalid repository page bounds.")
        return list(
            self.session.scalars(
                select(self.model)
                .order_by(self.model.created_at, self.model.id)
                .limit(limit)
                .offset(offset)
            )
        )

    def update(self, identity: str, **changes) -> T:
        record = self.get(identity)
        allowed = MUTABLE_FIELDS.get(self.model.__tablename__, set())
        if not changes.keys() <= allowed:
            raise ImmutableRecord("These record fields are immutable through the repository.")
        for name, value in changes.items():
            setattr(record, name, value)
        self.session.flush()
        return record

    def delete(self, identity: str) -> None:
        if self.model.__tablename__ not in DELETABLE:
            raise ImmutableRecord("Historical records cannot be deleted through the repository.")
        self.session.delete(self.get(identity))
        self.session.flush()
