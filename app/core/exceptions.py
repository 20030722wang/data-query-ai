"""Structured application exception hierarchy for enterprise-grade error handling."""

from typing import Any


class AppError(Exception):
    """Base application exception with structured error metadata.

    All domain exceptions inherit from this class, ensuring consistent
    error responses through FastAPI exception handlers.

    Attributes:
        code: Machine-readable error code (e.g. "SQL_NOT_READONLY").
        status_code: HTTP status code to return.
        detail: Optional human-readable detail string.
    """

    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    detail: str | None = None

    def __init__(self, message: str = "", detail: str | None = None) -> None:
        super().__init__(message)
        if detail is not None:
            self.detail = detail


class QueryTooShortError(AppError):
    """Query text is empty or whitespace-only."""
    code = "QUERY_TOO_SHORT"
    status_code = 422


class QueryTooLongError(AppError):
    """Query text exceeds the maximum allowed length."""
    code = "QUERY_TOO_LONG"
    status_code = 422


class NoSQLReadOnlyError(AppError):
    """SQL statement is not a read-only query (e.g. INSERT/DELETE/DROP)."""
    code = "SQL_NOT_READONLY"
    status_code = 400


class SQLValidationError(AppError):
    """SQL failed syntax validation in the database."""
    code = "SQL_VALIDATION_ERROR"
    status_code = 400


class SQLExecutionError(AppError):
    """SQL execution failed at runtime."""
    code = "SQL_EXECUTION_ERROR"
    status_code = 500


class ExternalServiceError(AppError):
    """A downstream service (ES, Qdrant, Embedding) returned an error."""
    code = "EXTERNAL_SERVICE_ERROR"
    status_code = 502


class ConfigurationError(AppError):
    """Application configuration is invalid or missing."""
    code = "CONFIGURATION_ERROR"
    status_code = 500
