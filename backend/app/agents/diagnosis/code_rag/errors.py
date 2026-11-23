"""Sanitized internal failures suitable for a future Manager service boundary."""


class RagError(Exception):
    """A stable error code and safe message, without source text or private paths."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class SourceRejected(RagError):
    """The requested source scope or ingestion policy is invalid."""


class EmbeddingUnavailable(RagError):
    """The real encoder is not installed, not available locally, or failed."""


class InvalidEmbedding(RagError):
    """A provider returned malformed, mismatched or non-finite vectors."""


class IndexUnavailable(RagError):
    """The private index or referenced evidence cannot be safely read."""


class RevisionConflict(RagError):
    """Immutable revision content or existing citation metadata conflicts."""
