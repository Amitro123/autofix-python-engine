"""
BanditAnalyzer

Programmatic adapter that runs Bandit on a Python code string and converts
Bandit's JSON results into domain AnalysisResult and CodeIssue entities.

This implementation uses the installed Bandit module by invoking it through
the current Python interpreter (python -m bandit) to ensure it works whether
the bandit console script is available in PATH or not.

Behavior:
- Writes the provided code to a temporary file.
- Runs bandit with JSON output against that temp file.
- Parses Bandit's JSON "results" and converts each finding into a CodeIssue.
- Maps Bandit confidence/severity to domain Severity values per mapping rules.
- Returns an AnalysisResult with analyzer_name="bandit" and the discovered issues.
- On Bandit failures (execution error, JSON parse error, unexpected output),
  returns an AnalysisResult with a single CRITICAL CodeIssue describing the failure.

Requirements satisfied:
- Implements AnalyzerInterface
- Uses Bandit (via python -m bandit invocation)
- Returns AnalysisResult from domain.entities.analysis_result
- Converts Bandit issues to CodeIssue and maps severities as documented
- Uses ErrorType.UNKNOWN for now
- Includes docstrings and error handling
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from typing import Any, List, Tuple, Optional

from autofix_core.application.interfaces.analyzer_interface import AnalyzerInterface
from autofix_core.domain.entities.analysis_result import AnalysisResult
from autofix_core.domain.entities.code_issue import CodeIssue
from autofix_core.domain.value_objects.severity import Severity
from autofix_core.domain.value_objects.error_type import ErrorType
from autofix_core.domain.exceptions import AnalysisError


class BanditAnalyzer(AnalyzerInterface):
    """
    Analyzer implementation that uses Bandit to detect security issues.

    Example:
        analyzer = BanditAnalyzer()
        result = analyzer.analyze(code="import os; os.system('ls')")

    The returned AnalysisResult contains CodeIssue entries for each security
    finding Bandit reports (mapped into our domain severity and error types).
    """

    analyzer_name = "bandit"

    def analyze(self, code: str, *, filename: Optional[str] = None) -> AnalysisResult:
        """
        Analyze the provided Python source code with Bandit.

        Parameters:
        - code: Python source code to analyze
        - filename: optional logical filename to attribute results to (if None,
                    a temporary filename is used)

        Returns:
        - AnalysisResult containing detected security issues (possibly empty).

        Notes:
        - This method attempts to handle Bandit failures gracefully by returning
          an AnalysisResult containing a single CRITICAL CodeIssue describing
          the analyzer failure (instead of raising), while also logging/wrapping
          the underlying problem in an AnalysisError.
        """
        # Write code to a temporary file so Bandit can scan it
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tf:
                temp_file = tf.name
                tf.write(code or "")
                tf.flush()

            # Build command: use current python interpreter to run bandit as a module.
            cmd = [sys.executable, "-m", "bandit", "-f", "json", "-q", temp_file]

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,  # avoid hanging indefinitely
            )

            if proc.returncode not in (0, 1):  # Bandit returns 1 when issues found
                # Treat non-standard return codes as analyzer failure
                err_msg = proc.stderr.strip() or f"Bandit exited with code {proc.returncode}"
                raise AnalysisError("bandit execution failed", details={"stderr": err_msg})

            # Parse JSON output
            try:
                payload = json.loads(proc.stdout)
            except json.JSONDecodeError as exc:
                raise AnalysisError("failed to parse bandit JSON output", details={"error": str(exc), "stdout": proc.stdout})

            results = payload.get("results", [])
            issues: List[CodeIssue] = []

            for item in results:
                try:
                    issue_text = item.get("issue_text") or item.get("issue") or "<no message>"
                    line = int(item.get("line_number") or item.get("line") or 1)
                    column = int(item.get("col_offset") or item.get("column") or 0)
                    file_path = item.get("filename") or filename or temp_file
                    confidence = (item.get("issue_confidence") or "").upper()
                    bandit_severity = (item.get("issue_severity") or "").upper()

                    severity = self._map_severity(confidence=confidence, severity=bandit_severity)

                    error_type = ErrorType.UNKNOWN  # TODO: refine mapping from bandit test_id -> ErrorType

                    ci = CodeIssue(
                        message=issue_text,
                        line=line if line >= 1 else 1,
                        column=column if column >= 0 else 0,
                        severity=severity,
                        error_type=error_type,
                        file_path=file_path,
                    )
                    issues.append(ci)
                except Exception as inner_exc:
                    # Skip problematic items but capture diagnostic as an AnalysisError
                    # We do not fail the whole analysis for one malformed result object.
                    # Optionally, append a CodeIssue representing the parsing problem.
                    issues.append(
                        CodeIssue(
                            message=f"failed to parse bandit result item: {inner_exc}",
                            line=1,
                            column=0,
                            severity=Severity.CRITICAL,
                            error_type=ErrorType.UNKNOWN,
                            file_path=filename or temp_file,
                        )
                    )

            return AnalysisResult(
                score=None,
                grade=None,
                issues=tuple(issues),
                analyzer_name=self.analyzer_name,
            )

        except AnalysisError as ae:
            # Return an AnalysisResult that indicates analyzer failure with a CRITICAL issue
            failure_issue = CodeIssue(
                message=f"Bandit analysis failed: {ae.message}",
                line=1,
                column=0,
                severity=Severity.CRITICAL,
                error_type=ErrorType.UNKNOWN,
                file_path=filename or (temp_file or "<memory>"),
            )
            return AnalysisResult(
                score=None,
                grade=None,
                issues=(failure_issue,),
                analyzer_name=self.analyzer_name,
            )
        except subprocess.TimeoutExpired as to_exc:
            failure_issue = CodeIssue(
                message=f"Bandit timed out: {to_exc}",
                line=1,
                column=0,
                severity=Severity.CRITICAL,
                error_type=ErrorType.UNKNOWN,
                file_path=filename or (temp_file or "<memory>"),
            )
            return AnalysisResult(
                score=None,
                grade=None,
                issues=(failure_issue,),
                analyzer_name=self.analyzer_name,
            )
        except Exception as exc:  # unexpected errors
            failure_issue = CodeIssue(
                message=f"Unexpected error running Bandit: {exc}",
                line=1,
                column=0,
                severity=Severity.CRITICAL,
                error_type=ErrorType.UNKNOWN,
                file_path=filename or (temp_file or "<memory>"),
            )
            return AnalysisResult(
                score=None,
                grade=None,
                issues=(failure_issue,),
                analyzer_name=self.analyzer_name,
            )
        finally:
            # Best effort clean up of the temp file
            try:
                if temp_file:
                    import os
                    os.unlink(temp_file)
            except Exception:
                # silently ignore cleanup failures
                pass

    @staticmethod
    def _map_severity(*, confidence: str, severity: str) -> Severity:
        """
        Map Bandit's confidence and severity strings to the domain Severity enum.

        Mapping rules:
        - CONFIDENCE_HIGH + SEVERITY_HIGH -> Severity.CRITICAL
        - CONFIDENCE_HIGH + SEVERITY_MEDIUM -> Severity.ERROR
        - CONFIDENCE_MEDIUM -> Severity.WARNING
        - CONFIDENCE_LOW -> Severity.INFO

        Unknown/other combinations default to Severity.WARNING.
        """
        conf = (confidence or "").upper()
        sev = (severity or "").upper()

        if conf == "HIGH" and sev == "HIGH":
            return Severity.CRITICAL
        if conf == "HIGH" and sev == "MEDIUM":
            return Severity.ERROR
        if conf == "MEDIUM":
            return Severity.WARNING
        if conf == "LOW":
            return Severity.INFO

        # Fallback heuristics
        if sev == "HIGH":
            return Severity.ERROR
        if sev == "MEDIUM":
            return Severity.WARNING
        if sev == "LOW":
            return Severity.INFO

        return Severity.WARNING

# TODO:
# - Add a small adapter that maps bandit test_id (e.g., "B602") to ErrorType variants.
# - Consider adding an async analyze_async variant or streaming results for large codebases.
# - Optionally, integrate bandit's config (skips, severity thresholds) via constructor args.