# tests/test_variable_tracking.py (NEW FILE)
from autofix_core.application.services.debugger_service import DebuggerService

def test_variable_tracking_simple():
    """Test basic variable tracking."""
    debugger = DebuggerService()
    
    result = debugger.execute_with_tracking(
        code="x = 10\nx = x + 5\nprint(x)"
    )
    
    assert result['success'] is True
    assert result['output'] == "15\n"
    assert len(result['tracking']['snapshots']) == 3
    assert len(result['tracking']['changes']) == 1

def test_variable_tracking_with_changes():
    """Test tracking multiple changes."""
    debugger = DebuggerService()
    
    result = debugger.execute_with_tracking(
        code="x = 10\nx = x * 2\nx = x + 5"
    )
    
    assert result['success'] is True
    assert result['tracking']['changes'][0]['old'] == '10'
    assert result['tracking']['changes'][0]['new'] == '20'
    assert result['tracking']['changes'][1]['old'] == '20'
    assert result['tracking']['changes'][1]['new'] == '25'

def test_variable_tracking_with_error():
    """Test tracking captures state at error."""
    debugger = DebuggerService()
    
    result = debugger.execute_with_tracking(
        code="x = 10\ny = [1, 2, 3]\nz = y[10]"
    )
    
    assert result['success'] is False
    assert result['error_type'] == 'IndexError'
    assert 'x' in result['variables_at_error']
    assert result['variables_at_error']['x'] == '10'
    # Partial tracking should work!
    assert len(result['tracking']['snapshots']) >= 2
