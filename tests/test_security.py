import pytest
from api.services.debugger_service import DebuggerService

@pytest.fixture
def debugger_service():
    """Provides a DebuggerService instance for testing."""
    return DebuggerService()

def test_sandbox_prevents_os_import(debugger_service):
    """
    Tests that the RestrictedPython sandbox prevents importing the 'os' module.
    """
    malicious_code = "import os"
    result = debugger_service.execute_with_trace(malicious_code)
    assert not result['success']
    assert result['error_type'] == 'ImportError'

def test_sandbox_prevents_file_access(debugger_service):
    """
    Tests that the RestrictedPython sandbox prevents file system access.
    """
    malicious_code = "open('README.md').read()"
    result = debugger_service.execute_with_trace(malicious_code)
    assert not result['success']
    assert result['error_type'] == 'NameError'

def test_sandbox_prevents_unsafe_attribute_access(debugger_service):
    """
    Tests that the RestrictedPython sandbox prevents accessing unsafe attributes.
    """
    malicious_code = "().__class__"
    result = debugger_service.execute_with_trace(malicious_code)
    assert not result['success']
    assert result['error_type'] == 'SyntaxError'