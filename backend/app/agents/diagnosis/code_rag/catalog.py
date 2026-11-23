"""Bind source roots and optional incident context using existing domain records."""

from pathlib import Path

from sqlalchemy import Engine, select
from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.db.types import validate_token
from app.models import Application, ApplicationRevision, Incident, RepositoryRevision, WorkflowRun
from app.repositories.unit_of_work import transaction

from .config import RagSettings
from .contracts import BoundSource, RetrievalRequest
from .errors import SourceRejected
from .ingestion import reject_redirects


class SourceCatalog:
    """No caller-supplied filesystem paths; revisions must already be registered."""

    def __init__(self, engine: Engine, settings: Settings, rag: RagSettings) -> None:
        self.engine, self.settings, self.rag = engine, settings, rag

    def revision(self, application_id: str, revision: str) -> RepositoryRevision:
        validate_token(application_id)
        validate_token(revision)
        with transaction(self.engine) as store:
            store.records(Application).get(application_id)
            record = store.session.scalar(
                select(RepositoryRevision).where(
                    RepositoryRevision.application_id == application_id,
                    RepositoryRevision.revision == revision,
                )
            )
            if record is None:
                raise SourceRejected(
                    "REVISION_UNAVAILABLE", "The source revision is not registered."
                )
            return record

    def bind(self, application_id: str, revision: str) -> BoundSource:
        """Bind only the current operator-permitted revision and reject write overlap."""
        record = self.revision(application_id, revision)
        with transaction(self.engine) as store:
            application = store.records(Application).get(application_id)
            selected = store.session.scalar(
                select(ApplicationRevision).where(
                    ApplicationRevision.application_id == application_id,
                )
            )
            permitted = self.settings.permitted_workspaces.get(application.workspace_key)
            if (
                not permitted
                or permitted.revision != revision
                or not selected
                or selected.revision_id != record.id
            ):
                raise SourceRejected(
                    "SOURCE_NOT_PERMITTED", "This source revision is not permitted for ingestion."
                )
            root = self.settings.demo_root / application.workspace_key
        reject_redirects(root)
        resolved = root.resolve(strict=True)
        resolved.relative_to(self.settings.demo_root.resolve(strict=True))
        destinations = [self.settings.artifact_root, self.rag.index_root, self.rag.model_root]
        database = make_url(str(self.engine.url)).database
        if database and database != ":memory:":
            destinations.append(Path(database).absolute())
        for destination in destinations:
            reject_redirects(destination)
            target = destination.resolve()
            if target == resolved or resolved in target.parents or target in resolved.parents:
                raise SourceRejected(
                    "STORAGE_OVERLAP", "Source and storage roots must be separate."
                )
        return BoundSource(application_id, revision, record.snapshot_artifact_id, resolved)

    def context(self, request: RetrievalRequest) -> None:
        """Validate incident/run linkage without requiring a current writable source tree."""
        self.revision(request.application_id, request.repository_revision)
        with transaction(self.engine) as store:
            if request.incident_id:
                incident = store.records(Incident).get(request.incident_id)
                if (incident.application_id, incident.repository_revision) != (
                    request.application_id,
                    request.repository_revision,
                ):
                    raise SourceRejected(
                        "SCOPE_MISMATCH", "Incident scope does not match retrieval."
                    )
            if request.run_id:
                run = store.records(WorkflowRun).get(request.run_id)
                if run.incident_id != request.incident_id:
                    raise SourceRejected("SCOPE_MISMATCH", "Run scope does not match retrieval.")
