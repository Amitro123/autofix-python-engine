"""
Tests for Enhanced GeminiService
Note: Most tests will be skipped unless GEMINI_API_KEY is set
"""

import pytest
import os
from api.services.gemini_service import GeminiService
from api.services.tools_service import ToolsService


# Skip all tests if no API key (for CI/CD)
pytestmark = pytest.mark.skipif(
    not os.getenv('GEMINI_API_KEY'),
    reason="GEMINI_API_KEY not set"
)


@pytest.fixture
def tools_service():
    """Create basic tools service"""
    return ToolsService()


@pytest.fixture
def gemini_service(tools_service):
    """Create Gemini service"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        pytest.skip("GEMINI_API_KEY not set")
    
    return GeminiService(tools_service, api_key=api_key)


class TestInitialization:
    """Test service initialization"""
    
    def test_init_with_api_key(self, tools_service):
        """Test initialization with API key"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            pytest.skip("No API key")
        
        service = GeminiService(tools_service, api_key=api_key)
        assert service.tools_service == tools_service
        assert service.history == []
    
    def test_init_creates_chat(self, gemini_service):
        """Test that chat session is created"""
        assert gemini_service.chat is not None


class TestCodeExtraction:
    """Test code extraction from responses"""
    
    def test_extract_python_code_block(self, gemini_service):
        """Test extracting Python code block"""
        response = """
Here's the fixed code:

```python
x = [1, 2, 3]
print(x[0])
```

This fixes the IndexError.
"""
        code = gemini_service._extract_code_from_response(response)
        assert "x = [1, 2, 3]" in code
        assert "print(x[0])" in code
    
    def test_extract_code_block_without_python_tag(self, gemini_service):
        """Test extracting code block without 'python' tag"""
        response = """
```
result = 5 + 3
print(result)
```
"""
        code = gemini_service._extract_code_from_response(response)
        assert "result = 5 + 3" in code
    
    def test_no_code_block_returns_full_text(self, gemini_service):
        """Test that full text returned if no code block"""
        response = "The code looks fine."
        code = gemini_service._extract_code_from_response(response)
        assert code == response.strip()


class TestChatReset:
    """Test chat reset functionality"""
    
    def test_reset_clears_history(self, gemini_service):
        """Test that reset clears history"""
        gemini_service.history = ["test"]
        gemini_service.reset_chat()
        assert gemini_service.history == []


# Note: We don't test actual API calls in unit tests
# Those should be in integration tests


if __name__ == "__main__":
    pytest.main([__file__, "-v"])