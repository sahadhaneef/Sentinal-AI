from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError, OperationalError, StatementError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Application, Incident, PatchCandidate, User
from app.repositories.application import ApplicationRepository
from app.repositories.base import Repository
from app.repositories.errors import Conflict, InvalidRecord, StorageUnavailable
from app.repositories.incident import IncidentRepository
from app.repositories.repair import PatchRepository


class Store:
    def __init__(self, session: Session):
        self.session = session
        self.users = Repository(session, User)
        self.applications = ApplicationRepository(session, Application)
        self.incidents = IncidentRepository(session, Incident)
        self.patches = PatchRepository(session, PatchCandidate)

    def records[T: Base](self, model: type[T]) -> Repository[T]:
        # Keep specialized invariants even when the generic entry point is used.
        specialized = {
            Application: self.applications,
            Incident: self.incidents,
            PatchCandidate: self.patches,
        }
        return specialized.get(model) or Repository(self.session, model)


@contextmanager
def transaction(engine: Engine) -> Iterator[Store]:
    """One commit boundary. Any error rolls back the whole caller-owned operation."""
    with Session(engine, expire_on_commit=False) as session:
        try:
            with session.begin():
                yield Store(session)
        except IntegrityError:
            raise Conflict(
                "A database uniqueness, relationship or integrity rule was violated."
            ) from None
        except OperationalError:
            raise StorageUnavailable(
                "The database is unavailable or busy; retry the operation."
            ) from None
        except StatementError:
            raise InvalidRecord("The record contains invalid persistence data.") from None
