"""
Value object: Severity

Describes how serious a CodeIssue is. Used for prioritization and reporting.
"""
from __future__ import annotations

from enum import Enum, auto


class Severity(Enum):
    """
    Severity levels used to rank issues found by analyzers and handlers.
    """
    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()

    def __str__(self) -> str:
        return self.name

# TODO: Consider attaching numeric priority values to severity levels if the
#       application requires sorting or thresholding logic.