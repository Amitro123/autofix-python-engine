"""
Pylint integration for Python code style checking.

Analyzes code for:
- Best practices
- Potential bugs
- Code style issues (via Pylint)
"""
from typing import Dict, List, Optional
import tempfile
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass
import shutil
import os
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class PylintIssue:
    """Represents a single Pylint issue."""
    line: int
    column: int
    severity: str  # error, warning, convention, refactor
    message: str
    rule_id: str
    symbol: str

    def to_dict(self) -> Dict:
        return {
            "line": self.line,
            "column": self.column,
            "severity": self.severity,
            "message": self.message,
            "rule_id": self.rule_id,
            "symbol": self.symbol,
        }


class PylintAnalyzer:
    """
    Wrapper around Pylint for code analysis.

    Usage:
        analyzer = PylintAnalyzer()
        result = analyzer.analyze("def foo():\\n  x=1")
    """

    def __init__(self, config: Optional[Dict] = None, pylint_bin: Optional[str] = None, timeout: int = 10):
        """
        Initialize Pylint analyzer.

        Args:
            config: Optional Pylint configuration
            pylint_bin: Optional path to pylint binary; if None, shutil.which is used
            timeout: subprocess timeout in seconds
        """
        self.config = config or self._default_config()
        self.timeout = timeout
        self.pylint_bin = pylint_bin or shutil.which("pylint")
        self.available = bool(self.pylint_bin)

    def analyze(self, code: str) -> Dict:
        """
        Analyze Python code with Pylint.

        Returns a dict with at least:
            - score: Optional[float]  (None if unavailable)
            - issues: list
            - error: optional error string when analysis failed
        """
        if not self.available:
            return {"score": None, "issues": [], "error": "pylint binary not found", "total_issues": 0}

        # Write code to temporary file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            result = self._run_pylint(temp_path)
            return self._parse_results(result)
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                logger.exception("Failed to remove temp pylint file %s", temp_path)

    def _run_pylint(self, file_path: Path) -> Dict:
        """
        Run Pylint on a file and return structured output.
        """
        cmd = [
            self.pylint_bin,
            str(file_path),
            "--output-format=json",
            "--score=yes",
            "--disable=missing-module-docstring,invalid-name",
            f"--max-line-length={self.config.get('max_line_length', 120)}",
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            return {"issues": [], "score": None, "error": "pylint timeout"}
        except FileNotFoundError:
            return {"issues": [], "score": None, "error": "pylint binary not found"}
        except Exception as e:
            logger.exception("Unexpected error running pylint: %s", e)
            return {"issues": [], "score": None, "error": f"pylint run error: {e}"}

        # Parse JSON output
        stdout = (proc.stdout or "").strip()
        try:
            issues = json.loads(stdout) if stdout else []
        except json.JSONDecodeError as e:
            # Return stderr for debugging/logging; don't leak directly to external clients
            return {
                "issues": [],
                "score": None,
                "error": f"Failed to parse Pylint output: {e}",
                "stdout": stdout,
                "stderr": proc.stderr,
            }

        score = self._extract_score(proc.stderr or "")
        return {"issues": issues, "score": score, "returncode": proc.returncode, "stderr": proc.stderr}

    def _extract_score(self, stderr: str) -> Optional[float]:
        """Extract Pylint score from stderr."""
        import re
        
        # Try multiple patterns:
        patterns = [
            r'rated at\s*([\d]+(?:\.\d+)?)/10',     # Standard format
            r'Your code has been rated at\s*([\d]+(?:\.\d+)?)/10',  # Verbose
            r'score:\s*([\d]+(?:\.\d+)?)',          # Alternative
        ]
        
        for pattern in patterns:
            match = re.search(pattern, stderr)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None

    def _parse_results(self, result: Dict) -> Dict:
        """
        Parse Pylint results into our format.
        """
        issues: List[PylintIssue] = []

        for item in result.get("issues", []):
            issue = PylintIssue(
                line=item.get("line", 0),
                column=item.get("column", 0),
                severity=item.get("type", "warning").lower(),
                message=item.get("message", ""),
                rule_id=item.get("message-id", ""),
                symbol=item.get("symbol", ""),
            )
            issues.append(issue)

        stats = self._calculate_stats(issues)
        score = result.get("score")  # may be None
        grade = self._score_to_grade(score) if score is not None else "N/A"

        return {
            "score": round(score, 2) if isinstance(score, (int, float)) else None,
            "grade": grade,
            "issues": [issue.to_dict() for issue in issues],
            "stats": stats,
            "total_issues": len(issues),
            "error": result.get("error"),
        }

    def _calculate_stats(self, issues: List[PylintIssue]) -> Dict:
        stats = {"error": 0, "warning": 0, "convention": 0, "refactor": 0}
        for issue in issues:
            severity = issue.severity.lower()
            if severity in stats:
                stats[severity] += 1
        return stats

    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 9.5:
            return "A+"
        if score >= 9.0:
            return "A"
        if score >= 8.5:
            return "A-"
        if score >= 8.0:
            return "B+"
        if score >= 7.5:
            return "B"
        if score >= 7.0:
            return "B-"
        if score >= 6.5:
            return "C+"
        if score >= 6.0:
            return "C"
        if score >= 5.5:
            return "C-"
        if score >= 5.0:
            return "D"
        return "F"

    def _default_config(self) -> Dict:
        """Default Pylint configuration."""
        return {"max_line_length": 120, "disable": ["missing-module-docstring", "invalid-name"]}