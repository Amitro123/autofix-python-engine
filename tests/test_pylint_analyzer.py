# tests/test_pylint_analyzer.py

"""Tests for PylintAnalyzer."""

import pytest
from api.services.analyzers import PylintAnalyzer


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
        
        assert result['score'] >= 9.0
        assert result['grade'] in ['A+', 'A', 'A-']
        assert result['total_issues'] <= 2
    
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
