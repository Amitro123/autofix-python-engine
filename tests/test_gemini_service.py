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
