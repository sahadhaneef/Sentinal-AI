"""Explicit operator-only metadata intake; never executes repositories or agents."""

import hashlib

from app import models
from app.core.config import Settings
from app.core.errors import ApiError
from app.core.logging import redact
from app.repositories.reads import ReadRepository
from app.repositories.unit_of_work import Store
from app.schemas.domain import ApplicationRegistration, IncidentIngestion
from app.services.artifacts import ArtifactReader, confined_path


class IntakeService:
    """Validate configured scope and write all intake metadata atomically."""

    def __init__(self, store: Store, settings: Settings) -> None:
        self.store = store
        self.settings = settings
        self.reads = ReadRepository(store.session)

    def register(self, request: ApplicationRegistration) -> models.Application:
        workspace = self.settings.permitted_workspaces.get(request.workspace_key)
        if workspace is None:
            raise ApiError(403, "FORBIDDEN", "This demo workspace is not permitted.")
        path = confined_path(self.settings.demo_root, request.workspace_key)
        if not path.is_dir():
            raise ApiError(403, "FORBIDDEN", "This demo workspace is not permitted.")
        data = ArtifactReader(self.store, self.settings).bytes_for_key(workspace.snapshot_key)
        digest = "sha256:" + hashlib.sha256(data).hexdigest()
        artifacts = self.reads.find(models.Artifact, storage_key=workspace.snapshot_key)
        if artifacts:
            artifact = artifacts[0]
            if (
                artifact.sha256 != digest
                or artifact.kind != "source_snapshot"
                or artifact.size_bytes != len(data)
            ):
                raise ApiError(
                    409, "CONFLICT", "Configured snapshot metadata does not match its artifact."
                )
        else:
            artifact = self.store.records(models.Artifact).add(
                models.Artifact(
                    kind="source_snapshot",
                    storage_key=workspace.snapshot_key,
                    sha256=digest,
                    content_type="application/octet-stream",
                    size_bytes=len(data),
                    redacted=False,
                )
            )
        application = self.store.applications.add(
            models.Application(
                name=workspace.name,
                description=workspace.description,
                workspace_key=request.workspace_key,
                status="offline",
                monitoring_enabled=False,
                supported_errors=workspace.supported_errors,
            )
        )
        revision = self.store.records(models.RepositoryRevision).add(
            models.RepositoryRevision(
                application_id=application.id,
                revision=workspace.revision,
                snapshot_artifact_id=artifact.id,
            )
        )
        self.store.applications.select_revision(application.id, revision.id)
        self.store.records(models.AuditEvent).add(
            models.AuditEvent(
                application_id=application.id,
                event_type="application_registered",
                actor_type="system",
                actor_key="configured_operator",
                payload_metadata={"workspace_key": request.workspace_key},
            )
        )
        return application

    def ingest(self, request: IncidentIngestion) -> models.Incident:
        request = request.model_copy(update={"message": redact(request.message)})
        application = self.store.applications.get(request.application_id)
        if application.workspace_key not in self.settings.permitted_workspaces:
            raise ApiError(403, "FORBIDDEN", "This demo workspace is not permitted for ingestion.")
        if (
            request.classification == "supported"
            and request.error_type not in application.supported_errors
        ):
            raise ApiError(
                422, "UNSUPPORTED_FAILURE", "This error type is not configured as supported."
            )
        if request.log_artifact_id:
            # Validate bytes, confinement and redacted flag before linking browser-readable logs.
            ArtifactReader(self.store, self.settings).text(request.log_artifact_id, {"log"})
        event, incident = self.store.incidents.record_monitoring_event(request)
        audits = self.reads.find(
            models.AuditEvent, application_id=application.id, event_type="observation_recorded"
        )
        if not any(
            audit.payload_metadata.get("monitoring_event_id") == event.id for audit in audits
        ):
            self.store.records(models.AuditEvent).add(
                models.AuditEvent(
                    application_id=application.id,
                    incident_id=incident.id,
                    event_type="observation_recorded",
                    actor_type="system",
                    actor_key="configured_operator",
                    payload_metadata={"monitoring_event_id": event.id},
                )
            )
        return incident
