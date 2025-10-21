"""
Unit tests for BanditAnalyzer.

These tests use monkeypatching to simulate Bandit's JSON output where appropriate
so they are fast and deterministic. Tests are skipped if the 'bandit' package
is not available in the environment (per project requirement).
"""
from __future__ import annotations

import json
import pytest
from types import SimpleNamespace

from autofix_core.infrastructure.analyzers.bandit_analyzer import BanditAnalyzer
from autofix_core.domain.entities.analysis_result import AnalysisResult
from autofix_core.domain.entities.code_issue import CodeIssue
from autofix_core.domain.value_objects.severity import Severity

import importlib.util

HAS_BANDIT = importlib.util.find_spec("bandit") is not None

pytestmark = pytest.mark.skipif(not HAS_BANDIT, reason="bandit package is not installed; skipping BanditAnalyzer tests")


def _make_bandit_stdout(results: list[dict]) -> str:
    """Serialize a bandit-style results payload to JSON as Bandit would emit."""
    return json.dumps({"results": results})


class TestBanditAnalyzer:
    """Test suite for BanditAnalyzer behavior and severity mapping."""

    def test_bandit_detects_hardcoded_password(self, monkeypatch, completed_process_factory):
        """
        Test that BanditAnalyzer detects hardcoded passwords and reports at least one issue.

        We simulate Bandit's JSON output for a hardcoded password finding and assert
        that the converted domain issues contain expected keywords and severities.
        """
        analyzer = BanditAnalyzer()

        # Simulate a Bandit result item for a hardcoded password
        result_item = {
            "issue_text": "Possible hardcoded password: password",
            "line_number": 1,
            "col_offset": 0,
            "filename": "test.py",
            "issue_confidence": "MEDIUM",
            "issue_severity": "LOW",
            "test_id": "B105",
        }
        stdout = _make_bandit_stdout([result_item])
        fake_proc = completed_process_factory(returncode=1, stdout=stdout, stderr="")

        # Monkeypatch subprocess.run used inside BanditAnalyzer to return our fake proc
        monkeypatch.setattr("autofix_core.infrastructure.analyzers.bandit_analyzer.subprocess.run", lambda *a, **k: fake_proc)

        result = analyzer.analyze(code='password = "hardcoded123"')

        assert isinstance(result, AnalysisResult), "Expected an AnalysisResult instance"
        assert result.analyzer_name == "bandit", "Analyzer name should be 'bandit'"
        assert len(result.issues) >= 1, "Expected at least one issue for hardcoded password"
        messages = " ".join([i.message.lower() for i in result.issues])
        assert ("password" in messages) or ("hardcoded" in messages), "Issue message should mention 'password' or 'hardcoded'"
        # Severity mapping for MEDIUM confidence should include WARNING at minimum
        assert any(i.severity in (Severity.WARNING, Severity.ERROR, Severity.CRITICAL) for i in result.issues), \
            "Expected severity to be WARNING, ERROR, or CRITICAL for hardcoded password"

    def test_bandit_detects_os_system(self, monkeypatch, completed_process_factory):
        """
        Test that BanditAnalyzer finds os.system usages and marks them as high-severity
        (ERROR or CRITICAL). We simulate a high-confidence/high-severity Bandit finding.
        """
        analyzer = BanditAnalyzer()

        result_item = {
            "issue_text": "Use of os.system detected, potential command injection",
            "line_number": 2,
            "col_offset": 4,
            "filename": "test.py",
            "issue_confidence": "HIGH",
            "issue_severity": "HIGH",
            "test_id": "B602",
        }
        stdout = _make_bandit_stdout([result_item])
        fake_proc = completed_process_factory(returncode=1, stdout=stdout, stderr="")

        monkeypatch.setattr("autofix_core.infrastructure.analyzers.bandit_analyzer.subprocess.run", lambda *a, **k: fake_proc)

        result = analyzer.analyze(code="import os\nos.system('ls')")

        assert isinstance(result, AnalysisResult), "Expected an AnalysisResult instance"
        assert len(result.issues) >= 1, "Expected at least one issue for os.system usage"
        # Ensure that at least one issue is ERROR or CRITICAL per mapping rules
        assert any(i.severity in (Severity.ERROR, Severity.CRITICAL) for i in result.issues), \
            "Expected severity to be ERROR or CRITICAL for os.system findings"
        assert any("command" in i.message.lower() or "injection" in i.message.lower() for i in result.issues), \
            "Expected message to mention command injection"

    def test_bandit_severity_mapping(self):
        """
        Validate BanditAnalyzer._map_severity mapping rules directly.

        - HIGH + HIGH -> CRITICAL
        - HIGH + MEDIUM -> ERROR
        - MEDIUM -> WARNING
        - LOW -> INFO
        """
        mapping = BanditAnalyzer._map_severity  # type: ignore[attr-defined]
        assert mapping(confidence="HIGH", severity="HIGH") == Severity.CRITICAL, "HIGH+HIGH should map to CRITICAL"
        assert mapping(confidence="HIGH", severity="MEDIUM") == Severity.ERROR, "HIGH+MEDIUM should map to ERROR"
        assert mapping(confidence="MEDIUM", severity="ANY") == Severity.WARNING, "MEDIUM confidence should map to WARNING"
        assert mapping(confidence="LOW", severity="ANY") == Severity.INFO, "LOW confidence should map to INFO"

    def test_bandit_handles_invalid_code(self, monkeypatch, completed_process_factory):
        """
        Ensure that BanditAnalyzer gracefully handles invalid Python code (syntax errors)
        by returning an AnalysisResult containing a CRITICAL issue rather than raising.
        """
        analyzer = BanditAnalyzer()

        # Simulate bandit failing with a non-standard return code and stderr
        fake_proc = completed_process_factory(returncode=2, stdout="", stderr="bandit crashed: syntax error")
        monkeypatch.setattr("autofix_core.infrastructure.analyzers.bandit_analyzer.subprocess.run", lambda *a, **k: fake_proc)

        result = analyzer.analyze(code="def broken(:\n    pass")

        assert isinstance(result, AnalysisResult), "Analyzer should return AnalysisResult on invalid code"
        assert len(result.issues) >= 1, "Result should contain at least one failure issue"
        assert all(isinstance(i, CodeIssue) for i in result.issues), "All issues should be CodeIssue instances"
        assert any(i.severity == Severity.CRITICAL for i in result.issues), "Failure should be reported as CRITICAL severity"

    def test_bandit_empty_code(self, monkeypatch, completed_process_factory):
        """
        Analyze empty source code string and ensure the analyzer returns an AnalysisResult
        with analyzer_name 'bandit' and no fatal errors.
        """
        analyzer = BanditAnalyzer()

        stdout = _make_bandit_stdout([])
        fake_proc = completed_process_factory(returncode=0, stdout=stdout, stderr="")
        monkeypatch.setattr("autofix_core.infrastructure.analyzers.bandit_analyzer.subprocess.run", lambda *a, **k: fake_proc)

        result = analyzer.analyze(code="")

        assert isinstance(result, AnalysisResult), "Expected AnalysisResult for empty code"
        assert result.analyzer_name == "bandit", "Analyzer name must be 'bandit'"
        assert isinstance(result.issues, tuple), "Issues should be a tuple"
        assert len(result.issues) == 0, "Empty code should produce no issues (results list empty)"

    def test_bandit_clean_code(self, monkeypatch, completed_process_factory):
        """
        Analyze a simple clean function and expect zero or minimal issues.
        """
        analyzer = BanditAnalyzer()

        stdout = _make_bandit_stdout([])  # bandit found no issues
        fake_proc = completed_process_factory(returncode=0, stdout=stdout, stderr="")
        monkeypatch.setattr("autofix_core.infrastructure.analyzers.bandit_analyzer.subprocess.run", lambda *a, **k: fake_proc)

        result = analyzer.analyze(code="def add(a, b):\n    return a + b")

        assert isinstance(result, AnalysisResult), "Expected AnalysisResult for clean code"
        assert len(result.issues) == 0, "Clean code should yield no security issues in most cases"