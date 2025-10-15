<<<<<<< HEAD
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

x =
print(x)

This fixes the IndexError.
"""
        code = gemini_service._extract_code_from_response(response)
        assert "x = [1, 2, 3]" in code
        assert "print(x[0])" in code
    
    def test_extract_code_block_without_python_tag(self, gemini_service):
        """Test extracting code block without 'python' tag"""
        response = """
result = 5 + 3
print(result)

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
=======
import pytest
import os
from unittest.mock import patch, MagicMock
from api.services.gemini_service import GeminiService

class TestGeminiService:
    """Test Gemini AI service functionality"""

    @pytest.mark.skip("Requires google.generativeai library")
    def test_gemini_is_enabled_with_api_key(self):
        """Test is_enabled returns True when GEMINI_API_KEY is set"""
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'}):
            service = GeminiService()
            assert service.is_enabled() == True

    def test_gemini_is_enabled_without_api_key(self):
        """Test is_enabled returns False when GEMINI_API_KEY is not set"""
        with patch.dict(os.environ, {}, clear=True):
            service = GeminiService()
            assert service.is_enabled() == False

    @pytest.mark.skip("Requires google.generativeai library")
    @patch('api.services.gemini_service.genai')
    def test_gemini_fix_code_success(self, mock_genai):
        """Test successful code fix with mocked Gemini API"""
        # Setup mock
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "```python\nprint('fixed code')\n```"
        mock_model.generate_content.return_value = mock_response

        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'}):
            service = GeminiService()
            service.model = mock_model

            result = service.fix_with_ai("print('broken')", "SyntaxError")

            assert result == "print('fixed code')"
            mock_model.generate_content.assert_called_once()

    @pytest.mark.skip("Requires google.generativeai library")
    @patch('api.services.gemini_service.genai')
    def test_gemini_fix_code_with_cache_hit(self, mock_genai):
        """Test cache hit prevents API call"""
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'}):
            service = GeminiService()

            # Mock cache to return cached result
            service.cache = MagicMock()
            service.cache.get.return_value = {'fixed_code': 'cached fix'}

            result = service.fix_with_ai("print('broken')", "SyntaxError")

            assert result == 'cached fix'
            # Should not call API since cache hit
            mock_genai.GenerativeModel.assert_not_called()

    @pytest.mark.skip("Requires google.generativeai library")
    @patch('api.services.gemini_service.genai')
    def test_gemini_error_handling(self, mock_genai):
        """Test error handling when API fails"""
        # Setup mock to raise exception
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API Error")

        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'}):
            service = GeminiService()
            service.model = mock_model

            result = service.fix_with_ai("print('broken')", "SyntaxError")

            assert result is None
            mock_model.generate_content.assert_called_once()

    def test_gemini_clean_response(self):
        """Test response cleaning removes markdown"""
        service = GeminiService()

        # Test with markdown code blocks
        dirty = "```python\nprint('hello')\n```"
        clean = service._clean_response(dirty)
        assert clean == "print('hello')"

        # Test without markdown
        clean = service._clean_response("print('hello')")
        assert clean == "print('hello')"

    @pytest.mark.skip("Requires google.generativeai library")
    @patch('api.services.gemini_service.genai')
    def test_gemini_token_counting(self, mock_genai):
        """Test token counting uses model.count_tokens"""
        mock_model = MagicMock()
        mock_token_result = MagicMock()
        mock_token_result.total_tokens = 50
        mock_model.count_tokens.return_value = mock_token_result

        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'}):
            service = GeminiService()
            service.model = mock_model

            tokens = service._count_tokens("print('test')", "SyntaxError")

            assert tokens == 50
            mock_model.count_tokens.assert_called_once()
>>>>>>> f5118b2815b33b1be97dee5d49e54cc1120e4622
