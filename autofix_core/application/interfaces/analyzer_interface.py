from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

# Forward reference to Domain types (to be created under domain.entities)
# from autofix_core.domain.entities import AnalysisResult

class AnalyzerInterface(ABC):
    """
    Abstract base class for analyzers (pylint, bandit, radon, etc.).

    Implementations in infrastructure/analyzers/ should implement this interface.

    Methods:
    - analyze: perform static analysis of source code and return a structured result.
    """

    @abstractmethod
    def analyze(self, code: str, *, filename: str | None = None) -> Any:
        """
        Analyze the provided source code and return a structured analysis result.

        Parameters:
        - code: source code to analyze
        - filename: optional filename to aid analyzers that use path heuristics

        Returns:
        - A domain AnalysisResult (or a serializable dict until AnalysisResult is implemented).
        """
        raise NotImplementedError

    # TODO:
    # - Define a concrete AnalysisResult class in domain.entities and update return type.
    # - Consider adding analyze_batch(files: dict[str, str]) -> list[AnalysisResult]