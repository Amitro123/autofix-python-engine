import pytest
import os
from unittest.mock import patch, MagicMock
from autofix_core.application.services.gemini_service import GeminiService
from autofix_core.application.services.tools_service import ToolsService

@pytest.fixture
def mock_tools_service():
    """Fixture for a mocked ToolsService."""
    mock = MagicMock(spec=ToolsService)
    mock.memory_service = MagicMock()
    return mock

class TestGeminiService:
    """Test Gemini AI service functionality"""

    @pytest.mark.skip("Requires google.generativeai library")
    @patch('os.getenv')
    def test_gemini_is_enabled_with_api_key(self, mock_getenv, mock_tools_service):
        """Test is_enabled returns True when GEMINI_API_KEY is set"""
        mock_getenv.return_value = 'test-key'
        service = GeminiService(tools_service=mock_tools_service)
        assert service.is_enabled() is True

    @patch('os.getenv')
    def test_gemini_is_enabled_without_api_key(self, mock_getenv, mock_tools_service):
        """Test is_enabled returns False when GEMINI_API_KEY is not set"""
        mock_getenv.return_value = None
        with pytest.raises(ValueError):
            GeminiService(tools_service=mock_tools_service)

    @pytest.mark.skip("Requires google.generativeai library")
    @patch('api.services.gemini_service.genai')
    @patch('os.getenv')
    def test_gemini_fix_code_success(self, mock_getenv, mock_genai, mock_tools_service):
        """Test successful code fix with mocked Gemini API"""
        mock_getenv.return_value = 'test-key'
        # Setup mock
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "```python\nprint('fixed code')\n```"
        mock_model.generate_content.return_value = mock_response

        service = GeminiService(tools_service=mock_tools_service)
        service.model = mock_model

        result = service.fix_with_ai("print('broken')", "SyntaxError")

        assert result == "print('fixed code')"
        mock_model.generate_content.assert_called_once()

    @pytest.mark.skip("Requires google.generativeai library")
    @patch('api.services.gemini_service.genai')
    @patch('os.getenv')
    def test_gemini_fix_code_with_cache_hit(self, mock_getenv, mock_genai, mock_tools_service):
        """Test cache hit prevents API call"""
        mock_getenv.return_value = 'test-key'
        service = GeminiService(tools_service=mock_tools_service)

        # Mock cache to return cached result
        service.cache = MagicMock()
        service.cache.get.return_value = {'fixed_code': 'cached fix'}

        result = service.fix_with_ai("print('broken')", "SyntaxError")

        assert result == 'cached fix'
        # Should not call API since cache hit
        mock_genai.GenerativeModel.assert_not_called()

    @pytest.mark.skip("Requires google.generativeai library")
    @patch('api.services.gemini_service.genai')
    @patch('os.getenv')
    def test_gemini_error_handling(self, mock_getenv, mock_genai, mock_tools_service):
        """Test error handling when API fails"""
        mock_getenv.return_value = 'test-key'
        # Setup mock to raise exception
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API Error")

        service = GeminiService(tools_service=mock_tools_service)
        service.model = mock_model

        result = service.fix_with_ai("print('broken')", "SyntaxError")

        assert result is None
        mock_model.generate_content.assert_called_once()

    @patch('os.getenv')
    def test_gemini_clean_response(self, mock_getenv, mock_tools_service):
        """Test response cleaning removes markdown"""
        mock_getenv.return_value = 'test-key'
        service = GeminiService(tools_service=mock_tools_service)

        # Test with markdown code blocks
        dirty = "```python\nprint('hello')\n```"
        clean = service._extract_code_from_response(dirty)
        assert clean == "print('hello')"

        # Test without markdown
        clean = service._extract_code_from_response("print('hello')")
        assert clean == "print('hello')"

    @pytest.mark.skip("Requires google.generativeai library")
    @patch('api.services.gemini_service.genai')
    @patch('os.getenv')
    def test_gemini_token_counting(self, mock_getenv, mock_genai, mock_tools_service):
        """Test token counting uses model.count_tokens"""
        mock_getenv.return_value = 'test-key'
        mock_model = MagicMock()
        mock_token_result = MagicMock()
        mock_token_result.total_tokens = 50
        mock_model.count_tokens.return_value = mock_token_result

        service = GeminiService(tools_service=mock_tools_service)
        service.model = mock_model

        tokens = service._count_tokens("print('test')", "SyntaxError")

        assert tokens == 50
        mock_model.count_tokens.assert_called_once()
