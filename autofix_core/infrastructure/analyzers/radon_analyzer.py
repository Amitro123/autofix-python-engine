"""
RadonAnalyzer

Adapter that runs radon complexity and maintainability metrics on a Python
source string and converts results into domain AnalysisResult and CodeIssue
entities.

Behavior:
- Computes maintainability index (MI) using radon.metrics.mi_visit
- Computes cyclomatic complexity for code blocks using radon.complexity.cc_visit
- Creates CodeIssue entries for functions/blocks with CC > 10 with severity:
    - 11-15 -> WARNING
    - 16-20 -> ERROR
    - >20   -> CRITICAL
- Sets AnalysisResult.score to the MI (float), grade to A/B/C/F per thresholds:
    - A: MI >= 20
    - B: MI >= 10
    - C: MI >= 0
    - F: MI < 0
- Uses ErrorType.UNKNOWN for all issues for now
- Gracefully handles radon errors and returns an AnalysisResult containing a
  CRITICAL CodeIssue describing the failure instead of raising.

Example:
    analyzer = RadonAnalyzer()
    result = analyzer.analyze(code="def complex():\n  ...")
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Optional, List, Tuple, Any

from autofix_core.application.interfaces.analyzer_interface import AnalyzerInterface
from autofix_core.domain.entities.analysis_result import AnalysisResult
from autofix_core.domain.entities.code_issue import CodeIssue
from autofix_core.domain.value_objects.severity import Severity
from autofix_core.domain.value_objects.error_type import ErrorType
from autofix_core.domain.exceptions import AnalysisError

# Import radon functions lazily so import-time failures can be handled at runtime
try:
    from radon.complexity import cc_visit  # type: ignore
    from radon.metrics import mi_visit  # type: ignore
except Exception:
    # If imports fail we will raise / handle at analyze() time.
    cc_visit = None  # type: ignore
    mi_visit = None  # type: ignore


class RadonAnalyzer(AnalyzerInterface):
    """
    Analyzer implementation that uses radon to compute maintainability index and
    cyclomatic complexity, returning an AnalysisResult with metrics and issues.

    The analyzer is synchronous and expects complete source code provided as a
    string.
    """

    analyzer_name = "radon"

    def analyze(self, code: str, *, filename: Optional[str] = None) -> AnalysisResult:
        """
        Analyze the provided Python source code using radon.

        Parameters:
        - code: Python source code string to analyze
        - filename: optional logical filename to attribute results to

        Returns:
        - AnalysisResult with:
            - score set to the maintainability index (float) when available
            - grade per MI thresholds
            - issues: CodeIssue instances for overly complex blocks
        """
        # Defensive: ensure radon is available
        if cc_visit is None or mi_visit is None:
            failure_issue = CodeIssue(
                message="Radon package is not available in the runtime environment",
                line=1,
                column=0,
                severity=Severity.CRITICAL,
                error_type=ErrorType.UNKNOWN,
                file_path=filename or "<memory>",
            )
            return AnalysisResult(
                score=None,
                grade=None,
                issues=(failure_issue,),
                analyzer_name=self.analyzer_name,
            )

        try:
            # Compute Maintainability Index (MI)
            # radon.metrics.mi_visit signature may vary between versions. Prefer
            # calling with two args where supported; fall back otherwise.
            mi_value: Optional[float]
            try:
                # many radon versions: mi_visit(code, True) -> float
                mi_value = float(mi_visit(code, True))
            except TypeError:
                # fallback: mi_visit(code)
                mi_value = float(mi_visit(code))

            # Determine grade
            grade = self._grade_from_mi(mi_value)

            issues: List[CodeIssue] = []

            # Compute cyclomatic complexity for all code blocks
            cc_results = cc_visit(code)
            for block in cc_results:
                try:
                    cc_value = int(getattr(block, "complexity", getattr(block, "cc", None) or 0))
                    name = getattr(block, "name", "<unknown>")
                    lineno = int(getattr(block, "lineno", getattr(block, "lineno", 1) or 1))
                    # radon blocks don't usually contain column info; default to 0
                    column = 0
                    file_path = filename or getattr(block, "filename", "<memory>")

                    # Only create an issue for CC > 10
                    if cc_value > 10:
                        sev = self._severity_from_cc(cc_value)
                        msg = f"{name} has cyclomatic complexity {cc_value}"
                        issue = CodeIssue(
                            message=msg,
                            line=max(1, lineno),
                            column=column,
                            severity=sev,
                            error_type=ErrorType.UNKNOWN,
                            file_path=file_path,
                        )
                        issues.append(issue)
                except Exception as inner_exc:
                    # If we can't parse a block, append a parsing issue but continue
                    issues.append(
                        CodeIssue(
                            message=f"Failed to parse radon CC block: {inner_exc}",
                            line=1,
                            column=0,
                            severity=Severity.WARNING,
                            error_type=ErrorType.UNKNOWN,
                            file_path=filename or "<memory>",
                        )
                    )

            return AnalysisResult(
                score=mi_value,
                grade=grade,
                issues=tuple(issues),
                analyzer_name=self.analyzer_name,
            )

        except Exception as exc:
            # Wrap unexpected radon failures into an AnalysisResult with a CRITICAL issue
            # so callers receive a structured response.
            failure_issue = CodeIssue(
                message=f"Radon analysis failed: {exc}",
                line=1,
                column=0,
                severity=Severity.CRITICAL,
                error_type=ErrorType.UNKNOWN,
                file_path=filename or "<memory>",
            )
            # Optionally re-raise a wrapped AnalysisError for programmatic handling
            # but per requirements we return an AnalysisResult instead of raising.
            return AnalysisResult(
                score=None,
                grade=None,
                issues=(failure_issue,),
                analyzer_name=self.analyzer_name,
            )

    @staticmethod
    def _grade_from_mi(mi: Optional[float]) -> Optional[str]:
        """
        Convert MI value into a grade string per specification:

        - A: MI >= 20
        - B: MI >= 10
        - C: MI >= 0
        - F: MI < 0

        If mi is None, returns None.
        """
        if mi is None:
            return None
        try:
            if mi >= 20:
                return "A"
            if mi >= 10:
                return "B"
            if mi >= 0:
                return "C"
            return "F"
        except Exception:
            return None

    @staticmethod
    def _severity_from_cc(cc: int) -> Severity:
        """
        Map cyclomatic complexity to Severity:

        - 11-15: WARNING
        - 16-20: ERROR
        - >20   : CRITICAL
        """
        if 11 <= cc <= 15:
            return Severity.WARNING
        if 16 <= cc <= 20:
            return Severity.ERROR
        if cc > 20:
            return Severity.CRITICAL
        # default (shouldn't be reached for cc > 10)
        return Severity.WARNING

# TODO:
# - Add unit tests validating MI/grade mapping and CC -> Severity thresholds.
# - Consider exposing configuration options (cc_threshold, mi_thresholds).
# - Optionally implement an async analyze_async for non-blocking runs.