import pytest
from api.services.debugger_service import DebuggerService, ExecutionMode

@pytest.fixture
def debugger():
    """Create a debugger service instance."""
    return DebuggerService()

class TestBasicExecution:
    """Test basic code execution in the debugger service."""

    def test_simple_print(self, debugger):
        """Test a simple print statement."""
        result = debugger.execute("print('Hello, World!')")
        assert result.success is True
        assert "Hello, World!" in result.output
        assert result.error is None

    def test_math_operations(self, debugger):
        """Test mathematical operations."""
        code = "result = 5 + 3 * 2\nprint(result)"
        result = debugger.execute(code)
        assert result.success is True
        assert "11" in result.output

    def test_error_in_code(self, debugger):
        """Test code that raises an error."""
        code = "x = [1, 2, 3]\nprint(x[10])"
        result = debugger.execute(code)
        assert result.success is False
        assert "IndexError" in result.error_type

class TestTracedExecution:
    """Test traced execution with variable capture."""

    def test_trace_simple_code(self, debugger):
        """Test tracing of simple code."""
        code = "a = 10\nb = 20\nc = a + b\nprint(c)"
        result = debugger.execute_with_trace(code)
        assert result['success'] is True
        assert "30" in result['stdout']
        assert "c" in result['variables_at_end']
        assert result['variables_at_end']['c']['value'] == 30

    def test_trace_error_code(self, debugger):
        """Test tracing of code that raises an error."""
        code = "a = 10\nb = 0\nc = a / b"
        result = debugger.execute_with_trace(code)
        assert result['success'] is False
        assert result['error_type'] == "ZeroDivisionError"
        assert "c" not in result['variables_at_error']

class TestSecurityRestrictions:
    """Test security restrictions of the debugger service."""

    def test_block_os_import(self, debugger):
        """Test that importing the 'os' module is blocked."""
        code = "import os\nprint(os.getcwd())"
        result = debugger.execute(code)
        assert result.success is False
        assert "ImportError" in result.error_type

    def test_block_file_open(self, debugger):
        """Test that file operations are blocked."""
        code = "f = open('/etc/passwd', 'r')"
        result = debugger.execute(code)
        assert result.success is False
        assert "NameError" in result.error_type # open is not defined

class TestTimeout:
    """Test the timeout functionality."""

    def test_timeout_infinite_loop(self, debugger):
        """Test that an infinite loop times out."""
        code = "while True:\n    pass"
        result = debugger.execute(code, timeout=1)
        assert result.success is False
        assert "TimeoutError" in result.error_type
