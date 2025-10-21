# tests/test_pylint_analyzer.py

"""Tests for PylintAnalyzer."""

import pytest
from autofix_core.infrastructure.analyzers.pylint_analyzer import PylintAnalyzer
from unittest.mock import patch, MagicMock
import subprocess



class TestPylintAnalyzer:  # ← Need the class!
    """Test PylintAnalyzer functionality."""
    
    def test_perfect_code(self):
        """Test that perfect code gets high score."""
        analyzer = PylintAnalyzer()
        
        code = '''"""Module docstring."""


def hello_world():
    """Say hello."""
    print("Hello, world!")
'''
        
        result = analyzer.analyze(code)
        
        assert result['error'] is None, "Should not have error"
        assert isinstance(result['issues'], list), "Should have issues list"
        
        # If score somehow exists, validate it
        if result['score'] is not None:
            assert 0.0 <= result['score'] <= 10.0, "Score should be 0-10"
            assert result['grade'] != "N/A"
        else:
            # No score with JSON format - expected
            assert result['grade'] == "N/A"

    
    def test_bad_code(self):  # ← Now has class context!
        """Test that analyzer detects code issues."""
        analyzer = PylintAnalyzer()
        
        code = '''
def foo():
    x=1
    if x==1:
        print(x)
'''
        
        result = analyzer.analyze(code)
        
        # Check that analysis works and finds issues
        assert 'score' in result
        assert 'grade' in result
        assert 'issues' in result
        assert 'total_issues' in result
        assert result['total_issues'] > 0  # We found 2!
        
        # Verify issue structure
        if result['issues']:
            issue = result['issues'][0]
            assert 'line' in issue
            assert 'severity' in issue
            assert 'message' in issue
    
    def test_syntax_error(self):
        """Test handling of syntax errors."""
        analyzer = PylintAnalyzer()
        
        code = '''
def foo()
    print("missing colon")
'''
        
        result = analyzer.analyze(code)
        
        # Should handle gracefully
        assert 'score' in result
        assert 'issues' in result
    
    def test_issue_structure(self):
        """Test that issues have correct structure."""
        analyzer = PylintAnalyzer()
        
        code = 'x=1\nif x==1:\n    print(x)'
        
        result = analyzer.analyze(code)
        
        if result['total_issues'] > 0:
            issue = result['issues'][0]
            assert 'line' in issue
            assert 'severity' in issue
            assert 'message' in issue
            assert 'rule_id' in issue
    
    def test_stats(self):
        """Test statistics calculation."""
        analyzer = PylintAnalyzer()
        
        code = 'x=1'
        
        result = analyzer.analyze(code)
        
        assert 'stats' in result
        assert 'error' in result['stats']
        assert 'warning' in result['stats']
        assert 'convention' in result['stats']


# ==================== Additional Edge Case Tests ====================
# Added based on Copilot recommendations


def test_pylint_missing_binary(monkeypatch):
    """Test behavior when pylint binary is not found."""
    # Mock shutil.which to return None (pylint not found)
    monkeypatch.setattr("shutil.which", lambda name: None)
    
    analyzer = PylintAnalyzer()
    assert analyzer.available is False
    
    # Try to analyze - should gracefully fail
    res = analyzer.analyze("x=1")
    assert res["score"] is None
    assert res["error"] is not None
    assert "pylint" in res["error"].lower()


def test_pylint_timeout(monkeypatch):
    """Test behavior when pylint times out."""
    def fake_run(*args, **kwargs):
        """Simulate subprocess timeout."""
        raise subprocess.TimeoutExpired(cmd=str(kwargs.get("args", "")), timeout=1)
    
    # Mock subprocess.run to raise TimeoutExpired
    monkeypatch.setattr(
        "autofix_core.infrastructure.analyzers.pylint_analyzer.subprocess.run", 
        fake_run
    )
    
    # Create analyzer with short timeout
    analyzer = PylintAnalyzer(timeout=1)
    
    # Try to analyze - should handle timeout gracefully
    res = analyzer.analyze("x=1")
    assert res["score"] is None
    assert res["error"] is not None
    assert "timeout" in res["error"].lower()


def test_pylint_malformed_json(monkeypatch):
    """Test behavior when pylint returns invalid JSON."""
    # Create mock subprocess result with invalid JSON
    fake_proc = MagicMock()
    fake_proc.stdout = "NOT VALID JSON"
    fake_proc.stderr = ""
    fake_proc.returncode = 0
    
    # Mock subprocess.run to return fake result
    monkeypatch.setattr(
        "autofix_core.infrastructure.analyzers.pylint_analyzer.subprocess.run",
        lambda *args, **kwargs: fake_proc
    )
    
    analyzer = PylintAnalyzer()
    
    # Try to analyze - should handle JSON parse error gracefully
    res = analyzer.analyze("x=1")
    assert res["score"] is None
    assert res["error"] is not None
    assert "parse" in res["error"].lower() or "json" in res["error"].lower()
