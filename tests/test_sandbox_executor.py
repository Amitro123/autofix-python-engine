"""
Tests for SandboxExecutor
Tests secure code execution with various security scenarios
"""

import pytest
from api.services.sandbox_executor import SandboxExecutor


@pytest.fixture
def sandbox():
    """Create sandbox executor"""
    return SandboxExecutor()


class TestBasicExecution:
    """Test basic code execution"""
    
    def test_simple_print(self, sandbox):
        """Test simple print statement"""
        result = sandbox.execute_code("print('Hello, World!')")
        
        assert result['success'] == True
        assert "Hello, World!" in result['stdout']
        assert result['exit_code'] == 0
    
    def test_math_operations(self, sandbox):
        """Test math operations"""
        code = """
result = 5 + 3 * 2
print(result)
"""
        result = sandbox.execute_code(code)
        
        assert result['success'] == True
        assert "11" in result['stdout']
    
    def test_safe_imports(self, sandbox):
        """Test that safe imports work"""
        code = """
    import math
    import json
    import re
    import time

    print("All safe imports work!")
    print(f"Math works: {math.pi:.2f}")
    print(f"JSON works: {json.dumps({'test': True})}")
    """
        result = sandbox.execute_code(code)
        
        assert result['success'] == True
        assert "All safe imports work!" in result['stdout']

    
    def test_error_in_code(self, sandbox):
        """Test code with errors"""
        code = "x = [1, 2, 3]\nprint(x[10])"
        result = sandbox.execute_code(code)
    
        assert result['success'] == False
        assert 'IndexError' in result['stderr']


class TestSecurityRestrictions:
    """Test security restrictions"""
    
    def test_block_os_import(self, sandbox):
        """Test that os module is blocked"""
        code = "import os\nprint(os.getcwd())"
        result = sandbox.execute_code(code)
        
        assert result['success'] == False
        assert 'ImportError' in result['stderr'] or 'blocked' in result['stderr'].lower()
    
    def test_block_subprocess_import(self, sandbox):
        """Test that subprocess is blocked"""
        code = "import subprocess\nsubprocess.run(['ls'])"
        result = sandbox.execute_code(code)
        
        assert result['success'] == False
        assert 'ImportError' in result['stderr']
    
    def test_block_socket_import(self, sandbox):
        """Test that socket is blocked"""
        code = "import socket\ns = socket.socket()"
        result = sandbox.execute_code(code)
        
        assert result['success'] == False
        assert 'ImportError' in result['stderr']
    
    def test_block_file_open(self, sandbox):
        """Test that file operations are blocked"""
        code = "f = open('/etc/passwd', 'r')"
        result = sandbox.execute_code(code)
        
        assert result['success'] == False
        assert 'PermissionError' in result['stderr'] or 'not allowed' in result['stderr'].lower()
    
    def test_block_eval(self, sandbox):
        """Test that eval is blocked"""
        code = "eval('print(1)')"
        result = sandbox.execute_code(code)
        
        assert result['success'] == False
        assert 'PermissionError' in result['stderr']
    
    def test_block_exec(self, sandbox):
        """Test that exec is blocked"""
        code = "exec('print(1)')"
        result = sandbox.execute_code(code)
        
        assert result['success'] == False
        assert 'PermissionError' in result['stderr']


class TestTimeout:
    """Test timeout functionality"""
    
    def test_timeout_infinite_loop(self, sandbox):
        """Test that infinite loops timeout"""
        code = "while True:\n    pass"
        result = sandbox.execute_code(code, timeout=1)
        
        assert result['success'] == False
        assert 'timeout' in result['error'].lower() or 'timeout' in result['stderr'].lower()
    
    def test_timeout_sleep(self, sandbox):
        """Test timeout with sleep"""
        code = "import time\ntime.sleep(10)"
        result = sandbox.execute_code(code, timeout=1)
        
        assert result['success'] == False


class TestComplexCode:
    """Test complex but safe code"""
    
    def test_list_comprehension(self, sandbox):
        """Test list comprehension"""
        code = """
numbers = [x**2 for x in range(10)]
print(sum(numbers))
"""
        result = sandbox.execute_code(code)
        
        assert result['success'] == True
        assert "285" in result['stdout']
    
    def test_function_definition(self, sandbox):
        """Test function definition and call"""
        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(10))
"""
        result = sandbox.execute_code(code)
        
        assert result['success'] == True
        assert "55" in result['stdout']
    
    def test_class_definition(self, sandbox):
        """Test class definition"""
        code = """
class Calculator:
    def add(self, a, b):
        return a + b

calc = Calculator()
print(calc.add(5, 3))
"""
        result = sandbox.execute_code(code)
        
        assert result['success'] == True
        assert "8" in result['stdout']


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
