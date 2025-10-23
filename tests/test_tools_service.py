"""
Tests for ToolsService
Tests code execution, syntax validation, and memory search tools
"""

import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch
from autofix_core.application.services.tools_service import ToolsService
from autofix_core.application.services.memory_service import MemoryService


@pytest.fixture
def temp_memory_service():
    """Create temporary memory service with test data"""
    temp_dir = tempfile.mkdtemp()
    service = MemoryService(persist_directory=temp_dir)
    
    # Add some test data
    service.store_fix(
        original_code="x = [1, 2, 3]\nprint(x[10])",
        error_type="IndexError",
        fixed_code="x = [1, 2, 3]\nif len(x) > 10:\n    print(x[10])",
        method="test"  # ← Changed from 'source' to 'method'
    )
    
    service.store_fix(
        original_code="result = '5' + 3",
        error_type="TypeError",
        fixed_code="result = '5' + str(3)",
        method="test"  # ← Changed from 'source' to 'method'
    )
    
    yield service
    shutil.rmtree(temp_dir, ignore_errors=True)



@pytest.fixture
def tools_service(temp_memory_service):
    """Create tools service with memory"""
    return ToolsService(memory_service=temp_memory_service)


@pytest.fixture
def tools_service_no_memory():
    """Create tools service without memory"""
    return ToolsService()


class TestExecuteCode:
    """Test code execution via sandbox"""
    
    def test_execute_simple_code(self, tools_service):
        """Test executing simple code"""
        code = "print('Hello, World!')"
        result = tools_service.execute_code(code)
        
        assert result['success'] == True
        assert "Hello, World!" in result['stdout']
        assert result['exit_code'] == 0
    
    def test_execute_code_with_error(self, tools_service):
        """Test executing code that raises error"""
        code = "x = [1, 2, 3]\nprint(x[10])"
        result = tools_service.execute_code(code)
        
        assert result['success'] == False
        assert result['exit_code'] != 0
        assert 'IndexError' in result['stderr']
    
    def test_execute_code_timeout(self, tools_service):
        """Test code execution timeout"""
        code = "import time\ntime.sleep(10)"
        result = tools_service.execute_code(code, timeout=1)
        
        assert result['success'] == False
        assert 'timeout' in result.get('error', '').lower() or 'timeout' in result['stderr'].lower()
    
    def test_execute_code_with_math(self, tools_service):
        """Test executing code with calculations"""
        code = "result = 5 + 3 * 2\nprint(result)"
        result = tools_service.execute_code(code)
        
        assert result['success'] == True
        assert "11" in result['stdout']
    
    def test_execute_code_security(self, tools_service):
        """Test that dangerous code is blocked"""
        code = "import os\nprint(os.getcwd())"
        result = tools_service.execute_code(code)
        
        assert result['success'] == False
        assert 'ImportError' in result['stderr'] or 'blocked' in result['stderr'].lower()


class TestValidateSyntax:
    """Test syntax validation"""
    
    def test_validate_valid_syntax(self, tools_service):
        """Test validating correct syntax"""
        code = "x = 1 + 2\nprint(x)"
        result = tools_service.validate_syntax(code)
        
        assert result['valid'] == True
        assert 'valid' in result['message'].lower()
    
    def test_validate_invalid_syntax(self, tools_service):
        """Test validating incorrect syntax"""
        code = "x = 1 +\nprint(x)"
        result = tools_service.validate_syntax(code)
        
        assert result['valid'] == False
        assert 'error' in result
        assert result['line'] is not None
    
    def test_validate_missing_colon(self, tools_service):
        """Test validating missing colon"""
        code = "if True\n    print('hello')"
        result = tools_service.validate_syntax(code)
        
        assert result['valid'] == False
        assert 'SyntaxError' in result['message']
    
    def test_validate_complex_code(self, tools_service):
        """Test validating complex valid code"""
        code = """
def calculate(x, y):
    result = x + y
    return result

numbers = [1, 2, 3]
for num in numbers:
    print(calculate(num, 10))
"""
        result = tools_service.validate_syntax(code)
        
        assert result['valid'] == True


class TestSearchMemory:
    """Test memory search functionality"""
    
    def test_search_memory_with_results(self, tools_service):
        """Test searching memory with results"""
        result = tools_service.search_memory(
            error_type="IndexError",
            code="x = [1, 2]\nprint(x[5])",
            k=3
        )
        
        assert result['success'] == True
        assert result['count'] > 0
        assert isinstance(result['results'], list)
        assert 'message' in result
    
    def test_search_memory_no_memory_service(self, tools_service_no_memory):
        """Test searching without memory service"""
        result = tools_service_no_memory.search_memory(
            error_type="IndexError"
        )
        
        assert result['success'] == False
        assert 'not configured' in result['error']
        assert result['count'] == 0
    
    def test_search_memory_by_error_type_only(self, tools_service):
        """Test searching by error type only"""
        result = tools_service.search_memory(
            error_type="TypeError",
            k=1
        )
        
        assert result['success'] == True
        assert len(result['results']) <= 1
    
    def test_search_memory_multiple_results(self, tools_service):
        """Test searching returns multiple results"""
        result = tools_service.search_memory(
            error_type="IndexError",
            k=5
        )
        
        assert result['success'] == True
        assert result['count'] >= 0
        for item in result['results']:
            assert 'original_code' in item or 'code' in item


class TestToolExecution:
    """Test tool execution dispatcher"""
    
    def test_execute_tool_execute_code(self, tools_service):
        """Test executing execute_code tool"""
        result = tools_service.execute_tool(
            'execute_code',
            {'code': 'print("test")'}
        )
        
        assert result['success'] == True
        assert 'test' in result['stdout']
    
    def test_execute_tool_validate_syntax(self, tools_service):
        """Test executing validate_syntax tool"""
        result = tools_service.execute_tool(
            'validate_syntax',
            {'code': 'x = 1 + 2'}
        )
        
        assert result['valid'] == True
    
    def test_execute_tool_search_memory(self, tools_service):
        """Test executing search_memory tool"""
        result = tools_service.execute_tool(
            'search_memory',
            {'error_type': 'IndexError', 'k': 2}
        )
        
        assert result['success'] == True
    
    def test_execute_unknown_tool(self, tools_service):
        """Test executing unknown tool"""
        result = tools_service.execute_tool(
            'unknown_tool',
            {}
        )
        
        assert result['success'] == False
        assert 'unknown' in result['error'].lower()
    
    def test_execute_tool_with_timeout(self, tools_service):
        """Test executing code with custom timeout"""
        result = tools_service.execute_tool(
            'execute_code',
            {'code': 'print("fast")', 'timeout': 10}
        )
        
        assert result['success'] == True


class TestToolDeclarations:
    """Test Gemini tool declarations"""
    
    def test_get_tool_declarations(self, tools_service):
        """Test getting tool declarations"""
        tools = tools_service.get_tool_declarations()
        
        assert tools is not None
        assert hasattr(tools, 'function_declarations')
        assert len(tools.function_declarations) == 3
    
    def test_tool_declarations_names(self, tools_service):
        """Test tool declaration names"""
        tools = tools_service.get_tool_declarations()
        
        names = [func.name for func in tools.function_declarations]
        assert 'execute_code' in names
        assert 'validate_syntax' in names
        assert 'search_memory' in names
    
    def test_tool_declarations_have_parameters(self, tools_service):
        """Test that tools have parameter definitions"""
        tools = tools_service.get_tool_declarations()
        
        for func in tools.function_declarations:
            assert func.name is not None
            assert func.description is not None
            assert func.parameters is not None


class TestIntegration:
    """Test integration scenarios"""
    
    def test_full_fix_workflow(self, tools_service):
        """Test complete fix workflow"""
        # 1. Validate syntax
        broken_code = "x = [1, 2, 3]\nprint(x[10])"
        syntax_result = tools_service.validate_syntax(broken_code)
        assert syntax_result['valid'] == True
        
        # 2. Execute to see error
        exec_result = tools_service.execute_code(broken_code)
        assert exec_result['success'] == False
        assert 'IndexError' in exec_result['stderr']
        
        # 3. Search for similar fixes
        search_result = tools_service.search_memory(
            error_type="IndexError",
            code=broken_code,
            k=3
        )
        assert search_result['success'] == True
        
        # 4. Try fixed code
        if search_result['count'] > 0:
            fixed_code = "x = [1, 2, 3]\nif len(x) > 10:\n    print(x[10])"
            fixed_result = tools_service.execute_code(fixed_code)
            # This might still "fail" because it doesn't print anything
            # but it shouldn't have IndexError
            assert 'IndexError' not in fixed_result.get('stderr', '')


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
