"""
Domain entity: AnalysisResult

Represents the outcome of running a static analyzer on a code unit.
This object is intended to be immutable once created.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple
import datetime

# Forward reference import pattern - CodeIssue lives in same package
from autofix_core.domain.entities.code_issue import CodeIssue


@dataclass(frozen=True)
class AnalysisResult:
    """
    Immutable result of a code analysis run.

    Attributes:
    - score: Optional numeric score (e.g., pylint score). Can be None if not applicable.
    - grade: Optional grade/label (e.g., 'A', 'B', 'C')
    - issues: Tuple of CodeIssue instances discovered by the analyzer
    - analyzer_name: Name of the analyzer (e.g., 'pylint', 'radon')
    - timestamp: UTC timestamp when analysis completed
    """
    score: Optional[float] = None
    grade: Optional[str] = None
    issues: Tuple[CodeIssue, ...] = field(default_factory=tuple)
    analyzer_name: str = ""
    timestamp: datetime.datetime = field(default_factory=lambda: datetime.datetime.utcnow())

    def __post_init__(self) -> None:
        # Validate score range if provided (common analyzers use 0..10 or 0..100)
        if self.score is not None:
            if not isinstance(self.score, (int, float)):
                raise TypeError("score must be numeric or None")
            # Allow general float ranges; don't enforce exact bounds here
            if self.score < 0:
                raise ValueError("score must be non-negative if provided")

        # Ensure issues is a tuple (immutable container)
        if not isinstance(self.issues, tuple):
            # object.__setattr__ allowed in frozen dataclass inside __post_init__
            object.__setattr__(self, "issues", tuple(self.issues))

    def __str__(self) -> str:
        return (
            f"AnalysisResult(analyzer={self.analyzer_name!r}, "
            f"score={self.score!r}, issues={len(self.issues)})"
        )

    # __repr__ is provided by dataclass; that's acceptable for AnalysisResult

# TODO: Add helper methods (e.g., highest_severity, issues_by_type) to assist
#       application logic, once business needs are clearer.