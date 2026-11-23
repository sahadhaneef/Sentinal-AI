"""Centralised exception types and HTTP error helpers."""
from __future__ import annotations

from typing import Any


class SentinelError(Exception):
    """Base application error."""

    code: str = "INTERNAL_ERROR"
    status: int = 500

    def __init__(self, message: str = "An unexpected error occurred.", details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details or {}


class NotFoundError(SentinelError):
    code = "NOT_FOUND"
    status = 404

    def __init__(self, resource: str = "Resource") -> None:
        super().__init__(f"{resource} not found.")


class ConflictError(SentinelError):
    code = "CONFLICT"
    status = 409


class ForbiddenError(SentinelError):
    code = "FORBIDDEN"
    status = 403

    def __init__(self, msg: str = "You do not have permission to perform this action.") -> None:
        super().__init__(msg)


class UnauthenticatedError(SentinelError):
    code = "UNAUTHENTICATED"
    status = 401

    def __init__(self) -> None:
        super().__init__("Authentication required.")


class ValidationError(SentinelError):
    code = "VALIDATION_ERROR"
    status = 422


class CandidateStaleError(SentinelError):
    code = "CANDIDATE_STALE"
    status = 409

    def __init__(self) -> None:
        super().__init__("Candidate revision does not match the demo workspace.")


class ApprovalRequiredError(SentinelError):
    code = "APPROVAL_REQUIRED"
    status = 409

    def __init__(self) -> None:
        super().__init__("Approve this exact candidate before applying.")


class TestsNotPassedError(SentinelError):
    code = "TESTS_NOT_PASSED"
    status = 409

    def __init__(self) -> None:
        super().__init__("All required checks must pass before approval.")


class UnsupportedFailureError(SentinelError):
    code = "UNSUPPORTED_FAILURE"
    status = 422


class RateLimitError(SentinelError):
    code = "RATE_LIMITED"
    status = 429
