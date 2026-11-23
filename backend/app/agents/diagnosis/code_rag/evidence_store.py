"""Immutable artifact writes and citation resolution using Phase 2/3 domain tables."""

import json
import os
from typing import Any

from sqlalchemy import Engine, select

from app.core.config import Settings
from app.core.logging import redact
from app.models import Artifact, CodeIndexEntry
from app.repositories.unit_of_work import Store, transaction
from app.services.artifacts import ArtifactReader, confined_path

from .contracts import BoundSource, CodeChunk, SourceFile
from .errors import IndexUnavailable, RevisionConflict
from .hashing import canonical, digest, identity
from .ingestion import reject_redirects


class EvidenceStore:
    """No diagnosis conclusions or workflow writes; only sealed source and code citations."""

    def __init__(self, engine: Engine, settings: Settings) -> None:
        self.engine, self.settings = engine, settings

    def _artifact(self, store: Store, artifact_id: str, data: bytes, kind: str) -> str:
        content_hash = digest(data)
        key = f"code-rag/{kind}/{content_hash[7:9]}/{content_hash[7:]}"
        existing = store.session.get(Artifact, artifact_id)
        if existing:
            if (existing.sha256, existing.kind, existing.size_bytes) != (
                content_hash,
                kind,
                len(data),
            ):
                raise RevisionConflict(
                    "ARTIFACT_CONFLICT", "An immutable source artifact conflicts."
                )
            if self._read(store, artifact_id) != data:
                raise IndexUnavailable("ARTIFACT_CORRUPT", "Stored source integrity check failed.")
            return artifact_id
        # Storage keys are unique in the shared database, so reuse identical blobs across scopes.
        shared = store.session.scalar(select(Artifact).where(Artifact.storage_key == key))
        if shared is not None:
            if self._read(store, shared.id) != data or shared.kind != kind:
                raise IndexUnavailable("ARTIFACT_CONFLICT", "Artifact storage identity conflicts.")
            return shared.id
        target = self.settings.artifact_root / key
        reject_redirects(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with target.open("xb") as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
        except FileExistsError:
            if target.read_bytes() != data:
                raise IndexUnavailable(
                    "ARTIFACT_CORRUPT", "Stored source integrity check failed."
                ) from None
        store.records(Artifact).add(
            Artifact(
                id=artifact_id,
                kind=kind,
                storage_key=key,
                sha256=content_hash,
                size_bytes=len(data),
                content_type="text/plain; charset=utf-8",
                redacted=kind == "source_excerpt",
            )
        )
        store.session.flush()
        return artifact_id

    def _read(self, store: Store, artifact_id: str) -> bytes:
        artifact = store.records(Artifact).get(artifact_id)
        path = confined_path(self.settings.artifact_root, artifact.storage_key)
        # Every read is bounded, including non-public full-file and manifest artifacts.
        with path.open("rb") as stream:
            data = stream.read(4 * 1024 * 1024 + 1)
        if (
            len(data) > 4 * 1024 * 1024
            or len(data) != artifact.size_bytes
            or digest(data) != artifact.sha256
        ):
            raise IndexUnavailable("ARTIFACT_CORRUPT", "Stored source integrity check failed.")
        return data

    def persist(
        self,
        source: BoundSource,
        files: list[SourceFile],
        chunks: list[CodeChunk],
        snapshot_hash: str,
        manifest_ref: str,
    ) -> list[dict[str, str]]:
        """Commit all citation rows together; orphaned immutable blobs are safe to retry."""
        with transaction(self.engine) as store:
            file_refs = {}
            for file in files:
                file_refs[file.file_path] = self._artifact(
                    store,
                    identity("source-file", file.content_hash),
                    file.content.encode(),
                    "source_snapshot",
                )
            manifest = {
                "schema": 1,
                "application_id": source.application_id,
                "repository_revision": source.repository_revision,
                "snapshot_hash": snapshot_hash,
                "registered_snapshot_ref": source.registered_snapshot_ref,
                "files": {
                    file.file_path: {"hash": file.content_hash, "ref": file_refs[file.file_path]}
                    for file in files
                },
            }
            actual_ref = self._artifact(store, manifest_ref, canonical(manifest), "source_snapshot")
            if actual_ref != manifest_ref:
                raise RevisionConflict("MANIFEST_CONFLICT", "Source seal identity conflicts.")
            members = []
            for chunk in chunks:
                artifact_id = self._artifact(
                    store,
                    identity("excerpt", chunk.content_hash),
                    chunk.content.encode(),
                    "source_excerpt",
                )
                existing = store.session.scalar(
                    select(CodeIndexEntry).where(
                        CodeIndexEntry.application_id == source.application_id,
                        CodeIndexEntry.repository_revision == source.repository_revision,
                        CodeIndexEntry.file_path == chunk.file_path,
                        CodeIndexEntry.start_line == chunk.start_line,
                        CodeIndexEntry.end_line == chunk.end_line,
                    )
                )
                if existing is not None:
                    if (
                        existing.content_hash != chunk.content_hash
                        or existing.symbol != chunk.symbol
                        or self._read(store, existing.artifact_id) != chunk.content.encode()
                    ):
                        raise RevisionConflict(
                            "CITATION_CONFLICT", "Existing immutable citation conflicts."
                        )
                    evidence_id = existing.id
                else:
                    evidence_id = chunk.evidence_id
                    store.records(CodeIndexEntry).add(
                        CodeIndexEntry(
                            id=evidence_id,
                            application_id=source.application_id,
                            repository_revision=source.repository_revision,
                            file_path=chunk.file_path,
                            symbol=chunk.symbol,
                            start_line=chunk.start_line,
                            end_line=chunk.end_line,
                            content_hash=chunk.content_hash,
                            artifact_id=artifact_id,
                            index_metadata={
                                "language": chunk.language,
                                "strategy": chunk.strategy,
                                "source_snapshot_ref": manifest_ref,
                            },
                        )
                    )
                members.append({"evidence_id": evidence_id, "content_hash": chunk.content_hash})
            return members

    def resolve(
        self, application_id: str, revision: str, manifest_ref: str, evidence_id: str
    ) -> dict[str, Any]:
        """Reverify excerpt, complete source file, manifest and actual line range."""
        with transaction(self.engine) as store:
            entry = store.records(CodeIndexEntry).get(evidence_id)
            manifest = json.loads(self._read(store, manifest_ref))
            if (entry.application_id, entry.repository_revision) != (application_id, revision) or (
                manifest["application_id"],
                manifest["repository_revision"],
            ) != (application_id, revision):
                raise IndexUnavailable("CITATION_SCOPE", "Citation scope verification failed.")
            file = manifest["files"][entry.file_path]
            original = self._read(store, file["ref"])
            excerpt = self._read(store, entry.artifact_id)
            text = original.decode("utf-8")
            lines = text.splitlines(keepends=True)
            actual = "".join(lines[entry.start_line - 1 : entry.end_line]).encode()
            if (
                entry.end_line > len(lines)
                or len(excerpt.decode("utf-8")) > 4096
                or actual != excerpt
                or digest(original) != file["hash"]
                or digest(excerpt) != entry.content_hash
                or redact(text) != text
            ):
                raise IndexUnavailable("CITATION_CORRUPT", "Citation source verification failed.")
            return {
                "evidence_id": entry.id,
                "application_id": application_id,
                "repository_revision": revision,
                "file_path": entry.file_path,
                "symbol": entry.symbol,
                "start_line": entry.start_line,
                "end_line": entry.end_line,
                "artifact_id": entry.artifact_id,
                "excerpt": excerpt.decode("utf-8"),
                "content_hash": entry.content_hash,
                "language": entry.index_metadata.get("language", "unknown"),
                "source_snapshot_ref": manifest_ref,
                "source_file_ref": file["ref"],
                "source_file_hash": file["hash"],
            }

    def stack_log(self, application_id: str, revision: str, artifact_id: str) -> str:
        """Accept only a log already linked to an incident of this exact source scope."""
        from app.models import Incident, IncidentMonitoringEvent, MonitoringEvent

        with transaction(self.engine) as store:
            linked = store.session.scalar(
                select(Incident.id)
                .join(IncidentMonitoringEvent, IncidentMonitoringEvent.incident_id == Incident.id)
                .join(
                    MonitoringEvent,
                    MonitoringEvent.id == IncidentMonitoringEvent.monitoring_event_id,
                )
                .where(
                    Incident.application_id == application_id,
                    Incident.repository_revision == revision,
                    MonitoringEvent.log_artifact_id == artifact_id,
                )
                .limit(1)
            )
            if linked is None:
                raise IndexUnavailable("LOG_SCOPE", "The log is not linked to this source scope.")
            return ArtifactReader(store, self.settings).text(artifact_id, {"log"})[:16000]
