class PersistenceError(Exception):
    """Sanitized persistence failure; future API services map codes deliberately."""

    code = "PERSISTENCE_ERROR"


class NotFound(PersistenceError):
    code = "NOT_FOUND"


class Conflict(PersistenceError):
    code = "CONFLICT"


class InvalidRecord(PersistenceError):
    code = "VALIDATION_ERROR"


class ImmutableRecord(PersistenceError):
    code = "IMMUTABLE_RECORD"


class StorageUnavailable(PersistenceError):
    code = "STORAGE_UNAVAILABLE"
