from __future__ import annotations

from typing import Any

class AutoFixException(Exception):
    """
    Base exception for the AutoFix domain.

    All domain-specific exceptions should inherit from this class so callers
    can catch domain-level errors explicitly.
    """
    def __init__(self, message: str, *, details: Any | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        return f"AutoFixException: {self.message}"

class DomainValidationError(AutoFixException):
    """
    Raised when domain invariants or validation rules are violated.

    Example: an AnalysisResult is constructed with invalid fields.
    """
    pass

class AnalysisError(AutoFixException):
    """
    Raised when code analysis fails or returns inconsistent results.

    Use this to wrap lower-level analyzer errors for the application layer.
    """
    pass

class FixApplicationError(AutoFixException):
    """
    Raised when applying a computed fix to the target code fails.

    For example: patching failure, file system errors, or sandbox execution errors.
    """
    pass

class DependencyError(AutoFixException):
    """
    Raised when required external dependencies (repos, AI providers, etc.)
    are unavailable or misconfigured.
    """
    pass

# TODO: Add specialized exceptions as needed (e.g. AnalyzerTimeoutError,
#       ProviderRateLimitError) and ensure they carry structured metadata.