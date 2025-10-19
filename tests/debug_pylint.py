def test_bad_code(self):
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
    assert result['total_issues'] > 0  # ✅ This will pass! (we found 2)
    
    # Verify issue structure
    if result['issues']:
        issue = result['issues'][0]
        assert 'line' in issue
        assert 'severity' in issue
        assert 'message' in issue
