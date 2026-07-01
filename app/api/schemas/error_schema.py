"""Unified error response schemas for consistent API error formatting."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard structured error response for all API endpoints.

    Attributes:
        request_id: The X-Request-ID value, for log correlation.
        code: Machine-readable error code (e.g. "SQL_VALIDATION_ERROR").
        message: Human-readable error summary.
        detail: Optional extended detail string.
    """
    request_id: str
    code: str
    message: str
    detail: str | None = None
