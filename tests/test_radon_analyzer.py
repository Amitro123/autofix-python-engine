"""
Unit tests for RadonAnalyzer.

These tests mock radon functions to ensure fast, deterministic execution.
They also skip the suite if the 'radon' package is not present in the environment,
per project requirements.
"""
from __future__ import annotations

import pytest
import importlib.util
from types import SimpleNamespace

from autofix_core.infrastructure.analyzers.radon_analyzer import RadonAnalyzer, cc_visit, mi_visit
from autofix_core.domain.entities.analysis_result import AnalysisResult
from autofix_core.domain.entities.code_issue import CodeIssue
from autofix_core.domain.value_objects.severity import Severity

HAS_RADON = importlib.util.find_spec("radon") is not None

pytestmark = pytest.mark.skipif(not HAS_RADON, reason="radon package is not installed; skipping RadonAnalyzer tests")


class _FakeBlock:
    """
    Minimal fake object that resembles a radon CC block for testing.
    Attributes expected by RadonAnalyzer: complexity (or cc), name, lineno, filename.
    """
    def __init__(self, name: str, complexity: int, lineno: int = 1, filename: str = "<memory>"):
        self.name = name
        self.complexity = complexity
        self.lineno = lineno
        self.filename = filename


class TestRadonAnalyzer:
    """Test suite for RadonAnalyzer behavior, MI grading and CC -> Severity mapping."""

    def test_radon_calculates_mi_score(self, monkeypatch):
        """
        Ensure RadonAnalyzer returns a numeric maintainability index (score) for simple code.
        """
        analyzer = RadonAnalyzer()

        # Mock mi_visit to return 42.0 and cc_visit to return empty list
        monkeypatch.setattr("autofix_core.infrastructure.analyzers.radon_analyzer.mi_visit", lambda code, *args, **kwargs: 42.0)
        monkeypatch.setattr("autofix_core.infrastructure.analyzers.radon_analyzer.cc_visit", lambda code: [])

        result = analyzer.analyze(code="def simple():\n    return 1")

        assert isinstance(result, AnalysisResult), "Expected AnalysisResult from RadonAnalyzer"
        assert result.score is not None, "Expected a numeric MI score"
        assert isinstance(result.score, float), "MI score should be a float"
        assert 0.0 <= result.score <= 100.0, f"MI score should be between 0 and 100, got {result.score}"

    def test_radon_assigns_grade_correctly(self, monkeypatch):
        """
        Validate grade assignment for specific MI values by mocking mi_visit.
        """
        analyzer = RadonAnalyzer()

        # MI >= 20 -> A
        monkeypatch.setattr("autofix_core.infrastructure.analyzers.radon_analyzer.mi_visit", lambda code, *a, **k: 20.0)
        monkeypatch.setattr("autofix_core.infrastructure.analyzers.radon_analyzer.cc_visit", lambda code: [])
        res_a = analyzer.analyze(code="x")
        assert res_a.grade == "A", f"MI 20.0 should produce grade 'A', got {res_a.grade!r}"

        # MI >= 10 -> B
        monkeypatch.setattr("autofix_core.infrastructure.analyzers.radon_analyzer.mi_visit", lambda code, *a, **k: 10.5)
        res_b = analyzer.analyze(code="x")
        assert res_b.grade == "B", f"MI 10.5 should produce grade 'B', got {res_b.grade!r}"

        # MI >= 0 -> C
        monkeypatch.setattr("autofix_core.infrastructure.analyzers.radon_analyzer.mi_visit", lambda code, *a, **k: 5.0)
        res_c = analyzer.analyze(code="x")
        assert res_c.grade == "C", f"MI 5.0 should produce grade 'C', got {res_c.grade!r}"

        # MI < 0 -> F
        monkeypatch.setattr("autofix_core.infrastructure.analyzers.radon_analyzer.mi_visit", lambda code, *a, **k: -1.0)
        res_f = analyzer.analyze(code="x")
        assert res_f.grade == "F", f"MI -1.0 should produce grade 'F', got {res_f.grade!r}"

    def test_radon_detects_high_complexity(self, monkeypatch):
        """
        A block with cyclomatic complexity > 20 should produce a CRITICAL CodeIssue.
        """
        analyzer = RadonAnalyzer()

        # Mock mi_visit and provide a CC block with complexity 25
        monkeypatch.setattr("autofix_core.infrastructure.analyzers.radon_analyzer.mi_visit", lambda code, *a, **k: 30.0)
        monkeypatch.setattr(
            "autofix_core.infrastructure.analyzers.radon_analyzer.cc_visit",
            lambda code: [_FakeBlock(name="complex_fn", complexity=25, lineno=10)]
        )

        result = analyzer.analyze(code="def complex_fn():\n    pass")

        assert isinstance(result, AnalysisResult), "Expected AnalysisResult from RadonAnalyzer"
        assert len(result.issues) >= 1, "Expected at least one complexity issue for CC>20"
        assert any(i.severity == Severity.CRITICAL for i in result.issues), "Expected CRITICAL severity for CC>20"
        assert any("complexity" in i.message.lower() for i in result.issues), "Issue message should mention 'complexity'"

    def test_radon_handles_medium_complexity(self, monkeypatch):
        """
        A block with cyclomatic complexity between 11 and 15 should produce a WARNING.
        """
        analyzer = RadonAnalyzer()

        monkeypatch.setattr("autofix_core.infrastructure.analyzers.radon_analyzer.mi_visit", lambda code, *a, **k: 35.0)
        monkeypatch.setattr(
            "autofix_core.infrastructure.analyzers.radon_analyzer.cc_visit",
            lambda code: [_FakeBlock(name="medium_fn", complexity=12, lineno=5)]
        )

        result = analyzer.analyze(code="def medium_fn():\n    pass")

        assert len(result.issues) >= 1, "Expected at least one issue for medium complexity"
        assert any(i.severity == Severity.WARNING for i in result.issues), "Expected WARNING severity for CC 11-15"

    def test_radon_handles_simple_code(self, monkeypatch):
        """
        Simple code should produce no complexity issues and should still provide MI and grade.
        """
        analyzer = RadonAnalyzer()

        monkeypatch.setattr("autofix_core.infrastructure.analyzers.radon_analyzer.mi_visit", lambda code, *a, **k: 50.0)
        monkeypatch.setattr("autofix_core.infrastructure.analyzers.radon_analyzer.cc_visit", lambda code: [])

        result = analyzer.analyze(code="def simple():\n    return 1")

        assert isinstance(result, AnalysisResult), "Expected AnalysisResult for simple code"
        assert result.score is not None, "Expected MI score for simple code"
        assert result.grade in ("A", "B", "C", "F", None) , f"Unexpected grade value: {result.grade!r}"
        assert len(result.issues) == 0, "Simple code should not yield complexity issues"

    def test_radon_handles_syntax_error(self, monkeypatch):
        """
        When radon functions raise or behavior is unexpected (e.g., due to syntax errors),
        the analyzer should return an AnalysisResult with a CRITICAL issue describing the failure.
        """
        analyzer = RadonAnalyzer()

        # Simulate mi_visit raising an exception due to invalid code
        def raise_exc(code, *a, **k):
            raise RuntimeError("radon parse error")

        monkeypatch.setattr("autofix_core.infrastructure.analyzers.radon_analyzer.mi_visit", raise_exc)
        # cc_visit can be a no-op or also raise; ensure analyzer handles either case
        monkeypatch.setattr("autofix_core.infrastructure.analyzers.radon_analyzer.cc_visit", lambda code: (_ for _ in ()).throw(RuntimeError("cc error")) if False else [])

        result = analyzer.analyze(code="def broken(:\n    pass")

        assert isinstance(result, AnalysisResult), "Analyzer should return AnalysisResult on radon failures"
        assert len(result.issues) >= 1, "Result should contain at least one failure issue"
        assert any(i.severity == Severity.CRITICAL for i in result.issues), "Failure should be reported as CRITICAL severity"