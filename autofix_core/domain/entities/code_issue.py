"""
Domain entity: CodeIssue

Represents a single issue found during code analysis, including location,
severity and an error classification.

This dataclass is immutable (frozen=True) to keep domain objects stable once
constructed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from autofix_core.domain.value_objects.error_type import ErrorType
from autofix_core.domain.value_objects.severity import Severity


@dataclass(frozen=True)
class CodeIssue:
    """
    Immutable representation of a code issue discovered by an analyzer.

    Attributes:
    - message: Human-readable description of the issue
    - line: 1-based line number where the issue occurred (must be >= 1)
    - column: 0-based column index where the issue occurred (must be >= 0)
    - severity: Severity enum describing how serious the issue is
    - error_type: ErrorType enum classifying the issue
    - file_path: Optional path of the file containing the issue
    """
    message: str
    line: int
    column: int
    severity: Severity
    error_type: ErrorType
    file_path: Optional[str] = None

    def __post_init__(self) -> None:
        # Validation for location values
        if self.line < 1:
            raise ValueError(f"line must be >= 1, got {self.line!r}")
        if self.column < 0:
            raise ValueError(f"column must be >= 0, got {self.column!r}")

        # Validate enums types to fail fast on programmer errors
        if not isinstance(self.severity, Severity):
            raise TypeError("severity must be an instance of Severity enum")
        if not isinstance(self.error_type, ErrorType):
            raise TypeError("error_type must be an instance of ErrorType enum")

    def __str__(self) -> str:
        path = self.file_path or "<unknown>"
        return (
            f"{self.error_type.name}: {self.message} "
            f"at {path}:{self.line}:{self.column} ({self.severity.name})"
        )

    def __repr__(self) -> str:  # Explicit repr for clearer logs
        return (
            f"CodeIssue(message={self.message!r}, file_path={self.file_path!r}, "
            f"line={self.line!r}, column={self.column!r}, "
            f"severity={self.severity!r}, error_type={self.error_type!r})"
        )

# TODO: Add convenience constructors (from_pylint, from_bandit, ...) to adapt
#       analyzer-specific payloads into this domain shape.