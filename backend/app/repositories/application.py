from sqlalchemy import select

from app.models import Application, ApplicationRevision, RepositoryRevision
from app.repositories.base import Repository
from app.repositories.errors import Conflict


class ApplicationRepository(Repository[Application]):
    def select_revision(self, application_id: str, revision_id: str) -> ApplicationRevision:
        self.get(application_id)
        revision = Repository(self.session, RepositoryRevision).get(revision_id)
        if revision.application_id != application_id:
            raise Conflict("The revision does not belong to this application.")
        selection = self.session.scalar(
            select(ApplicationRevision).where(ApplicationRevision.application_id == application_id)
        )
        if selection is None:
            selection = ApplicationRevision(application_id=application_id, revision_id=revision_id)
            self.session.add(selection)
        else:
            selection.revision_id = revision_id
        self.session.flush()
        self.session.expire(selection, ["revision"])
        return selection
