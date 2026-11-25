"""Internal Diagnosis D1 indexing/retrieval facade; no LLM, routes or workflow side effects."""

import logging
from collections.abc import Sequence

from sqlalchemy import Engine

from app.agents.diagnosis.execution.control import ExecutionControl
from app.agents.diagnosis.repositories import (
    IndexedSnapshot,
    RetrievalRepositories,
    StandaloneIndexReader,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.core.logging import redact
from app.repositories.errors import PersistenceError

from .cache import Collection, VectorCache
from .catalog import SourceCatalog
from .chunking import CodeChunker
from .config import CHUNKER_VERSION, FILTER_VERSION, RagSettings
from .contracts import IndexReport, RetrievalRequest, RetrievalResult, RetrievedEvidence
from .embeddings import EmbeddingProvider, LocalSemanticProvider, validate_vectors
from .errors import EmbeddingUnavailable, IndexUnavailable, RagError, SourceRejected
from .evidence_store import EvidenceStore
from .hashing import canonical, digest, identity
from .ingestion import SourceIngestion
from .stacktrace import StackHint, exact_tier, hints, matching_path

LOGGER = logging.getLogger(__name__)


class CodeRag:
    """Dependency-injected, revision-scoped service callable by a future Diagnosis adapter."""

    def __init__(
        self,
        engine: Engine,
        settings: Settings,
        rag: RagSettings | None = None,
        provider: EmbeddingProvider | None = None,
        *,
        repositories: RetrievalRepositories | None = None,
        control: ExecutionControl | None = None,
    ) -> None:
        self.engine, self.settings = engine, settings
        self.control = control or ExecutionControl()
        self.rag = rag or RagSettings()
        self.provider = provider or LocalSemanticProvider(
            self.rag.model_root, self.rag.embedding_batch_size, self.rag.embedding_threads
        )
        self.catalog = SourceCatalog(engine, settings, self.rag, self.control)
        self.ingestion = SourceIngestion(self.rag)
        self.chunker = CodeChunker(self.rag)
        self.cache = VectorCache(self.rag.index_root)
        self.evidence = EvidenceStore(engine, settings)
        self.repositories = repositories or RetrievalRepositories(
            self.catalog, self.evidence, StandaloneIndexReader(self.cache)
        )
        self.catalog = self.repositories.source
        self.evidence = self.repositories.evidence
        self.chunk_profile = identity(
            "chunk-profile",
            CHUNKER_VERSION,
            self.rag.max_chunk_lines,
            self.rag.max_chunk_chars,
            self.rag.overlap_lines,
        )

    def _scope(self, application_id: str, revision: str) -> str:
        return identity("scope", application_id, revision)

    def _collection_key(self, application_id: str, revision: str) -> str:
        return identity(
            "collection",
            application_id,
            revision,
            self.provider.profile,
            self.provider.dimensions,
            self.chunk_profile,
        )

    def _vector_key(self, content_hash: str) -> str:
        return identity("vector", self.provider.profile, self.provider.dimensions, content_hash)

    def _documents(self, texts: Sequence[str]) -> list[list[float]]:
        try:
            return validate_vectors(
                self.provider.documents(texts), len(texts), self.provider.dimensions
            )
        except RagError:
            raise
        except Exception:
            raise EmbeddingUnavailable(
                "ENCODER_FAILED", "Embedding provider failed safely."
            ) from None

    def index(self, application_id: str, revision: str) -> IndexReport:
        """Capture current permitted bytes once; later mutations require a new revision."""
        source = self.catalog.bind(application_id, revision)
        scan = self.ingestion.scan(source)
        snapshot_hash = digest(
            canonical(
                {
                    "filter": FILTER_VERSION,
                    "extensions": sorted(self.rag.allowed_extensions),
                    "files": {file.file_path: file.content_hash for file in scan.files},
                }
            )
        )
        manifest_ref = identity("manifest", application_id, revision)
        self.cache.reserve(self._scope(application_id, revision), snapshot_hash, manifest_ref)
        chunks = [chunk for file in scan.files for chunk in self.chunker.chunks(source, file)]
        if len(chunks) > self.rag.max_chunks:
            raise SourceRejected("CHUNK_LIMIT", "The repository exceeds the chunk limit.")
        unique = {chunk.content_hash: chunk.content for chunk in chunks}
        keys = [self._vector_key(value) for value in unique]
        vectors = self.cache.vectors(keys, self.provider.dimensions)
        missing = [value for value in unique if self._vector_key(value) not in vectors]
        for offset in range(0, len(missing), self.rag.embedding_batch_size):
            batch = missing[offset : offset + self.rag.embedding_batch_size]
            for content_hash, vector in zip(
                batch, self._documents([unique[value] for value in batch]), strict=True
            ):
                vectors[self._vector_key(content_hash)] = vector
        # Re-scan before publication to detect concurrent changes during embedding.
        after = self.ingestion.scan(source)
        if [(file.file_path, file.content_hash) for file in after.files] != [
            (file.file_path, file.content_hash) for file in scan.files
        ]:
            raise SourceRejected(
                "SOURCE_CHANGED", "Source changed during indexing; register stable source."
            )
        members = self.evidence.persist(source, scan.files, chunks, snapshot_hash, manifest_ref)
        for member in members:
            member["vector_key"] = self._vector_key(member["content_hash"])
        self.cache.publish(
            Collection(
                key=self._collection_key(application_id, revision),
                scope=self._scope(application_id, revision),
                snapshot_hash=snapshot_hash,
                manifest_ref=manifest_ref,
                members=members,
            ),
            vectors,
        )
        LOGGER.info(
            "Code index published",
            extra={
                "application_id": application_id,
                "repository_revision": revision,
                "chunks": len(chunks),
            },
        )
        return IndexReport(
            application_id=application_id,
            repository_revision=revision,
            source_snapshot_ref=manifest_ref,
            snapshot_hash=snapshot_hash,
            files=len(scan.files),
            chunks=len(chunks),
            embedded=len(missing),
            cached=len(unique) - len(missing),
            skipped=scan.skipped,
            provider_id=self.provider.profile,
        )

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """Return verified evidence or explicit empty/unavailable status, never a diagnosis."""
        try:
            self.control.checkpoint("before_revision")
            self.catalog.context(request)
            self.control.checkpoint("before_index")
            collection = self.repositories.index.collection(
                self._collection_key(request.application_id, request.repository_revision)
            )
            if collection is None:
                raise IndexUnavailable(
                    "REVISION_NOT_INDEXED", "The revision/profile has not been indexed."
                )
            if len(collection.members) > self.rag.max_chunks:
                raise IndexUnavailable(
                    "INDEX_LIMIT", "The index exceeds configured retrieval limits."
                )
            return self._retrieve(request, collection)
        except (
            RagError,
            PersistenceError,
            ApiError,
            OSError,
            ValueError,
            KeyError,
            TypeError,
        ) as error:
            code = (
                error.code
                if isinstance(error, (RagError, PersistenceError, ApiError))
                else "EVIDENCE_UNAVAILABLE"
            )
            return RetrievalResult(
                application_id=request.application_id,
                repository_revision=request.repository_revision,
                status="unavailable",
                reason=code,
                semantic_used=False,
                evidence=[],
            )

    def _retrieve(self, request: RetrievalRequest, collection: IndexedSnapshot) -> RetrievalResult:
        trace = redact(request.stack_trace)
        if request.stack_trace_ref:
            trace += "\n" + self.evidence.stack_log(
                request.application_id, request.repository_revision, request.stack_trace_ref
            )
        verified = []
        corrupt = False
        for member in collection.members:
            self.control.checkpoint("retrieval_member")
            try:
                item = self.evidence.resolve(
                    request.application_id,
                    request.repository_revision,
                    collection.manifest_ref,
                    member["evidence_id"],
                )
                if item["content_hash"] != member["content_hash"]:
                    raise IndexUnavailable("CITATION_CORRUPT", "Citation hash conflicts.")
                verified.append((member, item))
            except (RagError, PersistenceError, ApiError, OSError, ValueError, KeyError):
                corrupt = True
        paths = {item["file_path"] for _, item in verified}
        frames = []
        for frame in hints(trace):
            path = matching_path(frame.file_path, paths)
            if path:
                frames.append(StackHint(path, frame.line, frame.symbol))
        query = redact(
            "\n".join((request.error_type, request.error_message, request.search_query, trace))
        )[:8000]
        scores: dict[str, float] = {}
        semantic_used = False
        reason = "OK"
        if verified:
            try:
                self.control.checkpoint("before_embedding")
                query_vector = validate_vectors(
                    [self.provider.query(query)], 1, self.provider.dimensions
                )[0]
                self.control.checkpoint("after_embedding")
                vectors = self.repositories.index.vectors(
                    [member["vector_key"] for member, _ in verified], self.provider.dimensions
                )
                for key, vector in vectors.items():
                    self.control.checkpoint("retrieval_vector")
                    normalized = validate_vectors([vector], 1, self.provider.dimensions)[0]
                    scores[key] = max(
                        -1.0,
                        min(1.0, sum(a * b for a, b in zip(query_vector, normalized, strict=True))),
                    )
                semantic_used = len(vectors) == len(
                    {member["vector_key"] for member, _ in verified}
                )
                if not semantic_used:
                    reason = "EMBEDDINGS_MISSING"
            except Exception:
                reason = "EMBEDDINGS_UNAVAILABLE"
        results = []
        for member, item in verified:
            self.control.checkpoint("retrieval_rank")
            tier = exact_tier(
                item["file_path"], item["symbol"], item["start_line"], item["end_line"], frames
            )
            similarity = scores.get(member["vector_key"])
            if not tier and (similarity is None or similarity < self.rag.min_semantic_score):
                continue
            scaled = (similarity + 1) / 2 if similarity is not None else 0
            score = 0.4 * tier + 0.2 * scaled
            method = (
                "hybrid"
                if tier and similarity is not None
                else "stack_line"
                if tier == 2
                else "stack_symbol"
                if tier
                else "semantic"
            )
            results.append(
                RetrievedEvidence(
                    **item,
                    retrieval_method=method,
                    rank=1,
                    score=score,
                    semantic_score=similarity,
                    exact_tier=tier,
                )
            )
        results.sort(
            key=lambda item: (-item.score, item.file_path, item.start_line, item.evidence_id)
        )
        results = results[: request.top_k]
        for rank, item in enumerate(results, 1):
            item.rank = rank
        degraded = corrupt or (bool(verified) and not semantic_used)
        return RetrievalResult(
            application_id=request.application_id,
            repository_revision=request.repository_revision,
            status="partial"
            if degraded and results
            else "unavailable"
            if degraded
            else "ready"
            if results
            else "empty",
            reason="CITATIONS_UNAVAILABLE" if corrupt else reason,
            semantic_used=semantic_used,
            evidence=results,
        )
