"""Custom exception hierarchy for DealGuard."""

from typing import Any


class DealGuardError(Exception):
    """Base exception for all DealGuard errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


# ----- Authentication Errors -----


class AuthenticationError(DealGuardError):
    """Authentication failed."""

    pass


class TokenExpiredError(AuthenticationError):
    """JWT token has expired."""

    pass


class TokenInvalidError(AuthenticationError):
    """JWT token is invalid."""

    pass


class UnauthorizedError(DealGuardError):
    """User is not authorized to perform this action."""

    pass


# ----- Resource Errors -----


class NotFoundError(DealGuardError):
    """Requested resource was not found."""

    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(
            message=f"{resource} nicht gefunden",
            details={"resource": resource, "identifier": identifier},
        )


class ConflictError(DealGuardError):
    """Resource conflict (e.g., duplicate)."""

    pass


# ----- Validation Errors -----


class ValidationError(DealGuardError):
    """Input validation failed."""

    pass


class FileTooLargeError(ValidationError):
    """Uploaded file exceeds size limit."""

    def __init__(self, max_size_mb: int) -> None:
        super().__init__(
            message=f"Datei ist zu groß. Maximale Größe: {max_size_mb} MB",
            details={"max_size_mb": max_size_mb},
        )


class UnsupportedFileTypeError(ValidationError):
    """File type is not supported."""

    def __init__(self, file_type: str, supported: list[str]) -> None:
        super().__init__(
            message=f"Dateityp '{file_type}' wird nicht unterstützt",
            details={"file_type": file_type, "supported_types": supported},
        )


# ----- External Service Errors -----


class ExternalServiceError(DealGuardError):
    """Error from an external service."""

    pass


class AIServiceError(ExternalServiceError):
    """Error from AI service (Anthropic)."""

    pass


class AIRateLimitError(AIServiceError):
    """AI service rate limit exceeded."""

    pass


class StorageError(ExternalServiceError):
    """Error from storage service (S3)."""

    pass


# ----- Business Logic Errors -----


class QuotaExceededError(DealGuardError):
    """User has exceeded their plan quota."""

    def __init__(self, resource: str, limit: int) -> None:
        super().__init__(
            message=f"Limit erreicht: {limit} {resource} pro Monat",
            details={"resource": resource, "limit": limit},
        )


class AnalysisFailedError(DealGuardError):
    """Contract analysis failed."""

    pass
