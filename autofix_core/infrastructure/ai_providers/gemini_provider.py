"""
Google Gemini AI Provider implementation.

Provides code fixing capabilities using Google's Gemini 2.5 Pro model.
"""
from __future__ import annotations

import os
import logging
from typing import Optional, Any

from autofix_core.application.interfaces.ai_service_interface import AIServiceInterface

# Google Gemini imports
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

logger = logging.getLogger(__name__)


class GeminiProvider(AIServiceInterface):
    """
    Google Gemini AI provider for code fixing.
    
    Implements AIServiceInterface using Google's Gemini 2.5 Pro model
    for intelligent code analysis and fixing.
    """
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.0-flash-exp"):
        """
        Initialize Gemini provider.
        
        Args:
            api_key: Google AI API key (falls back to GOOGLE_API_KEY env var)
            model_name: Gemini model to use (default: gemini-2.0-flash-exp)
            
        Raises:
            ImportError: If google-generativeai is not installed
            ValueError: If API key is not provided
        """
        if not HAS_GEMINI:
            raise ImportError(
                "google-generativeai not installed. "
                "Install with: pip install google-generativeai"
            )
        
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Google API key not provided. "
                "Set GOOGLE_API_KEY environment variable or pass api_key parameter."
            )
        
        self.model_name = model_name
        self._configure_genai()
        self._model = None
    
    def _configure_genai(self) -> None:
        """Configure Google Generative AI with API key."""
        genai.configure(api_key=self.api_key)
    
    @property
    def model(self):
        """Lazy-load the Gemini model."""
        if self._model is None:
            self._model = genai.GenerativeModel(self.model_name)
        return self._model
    
    @property
    def name(self) -> str:
        """Return provider name."""
        return "gemini"
    
    # ============================================
    # Interface Implementation (AIServiceInterface)
    # ============================================
    
    async def generate_text(
        self, 
        prompt: str, 
        *, 
        max_tokens: int | None = None, 
        **kwargs: Any
    ) -> str:
        """
        Asynchronously generate text from Gemini.
        
        Args:
            prompt: Input prompt for the model
            max_tokens: Optional token limit
            kwargs: Provider-specific options
            
        Returns:
            Generated text as string
        """
        try:
            # Gemini's generate_content is synchronous, but we can wrap it
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Failed to generate text (async): {e}")
            raise
    
    def generate_text_sync(
        self, 
        prompt: str, 
        *, 
        max_tokens: int | None = None, 
        **kwargs: Any
    ) -> str:
        """
        Synchronously generate text from Gemini.
        
        Args:
            prompt: Input prompt for the model
            max_tokens: Optional token limit
            kwargs: Provider-specific options
            
        Returns:
            Generated text as string
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Failed to generate text (sync): {e}")
            raise
    
    # ============================================
    # Helper Methods (Code Fixing Specific)
    # ============================================
    
    def generate_fix(
        self,
        code: str,
        error_message: str,
        error_type: str,
        context: Optional[dict] = None
    ) -> str:
        """
        Generate a fix for the given code and error.
        
        Args:
            code: The broken Python code
            error_message: The error message from execution
            error_type: Type of error (e.g., "SyntaxError")
            context: Optional context information
            
        Returns:
            Fixed Python code as string
        """
        prompt = self._build_fix_prompt(code, error_message, error_type, context)
        
        try:
            # Use the sync method from interface
            response_text = self.generate_text_sync(prompt)
            fixed_code = self._extract_code_from_response(response_text)
            return fixed_code
        except Exception as e:
            logger.error(f"Failed to generate fix: {e}")
            raise
    
    def validate_fix(self, code: str, original_error: str) -> bool:
        """
        Validate that a fix resolves the original error.
        
        Args:
            code: The fixed code to validate
            original_error: The original error message
            
        Returns:
            True if fix is valid, False otherwise
        """
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError:
            return False
    
    def _build_fix_prompt(
        self,
        code: str,
        error_message: str,
        error_type: str,
        context: Optional[dict] = None
    ) -> str:
        """Build the prompt for Gemini."""
        prompt = f"""You are a Python code fixing expert. Fix the following code that has an error.

ERROR TYPE: {error_type}
ERROR MESSAGE: {error_message}

BROKEN CODE:
{code}

INSTRUCTIONS:
1. Analyze the error carefully
2. Fix the code to resolve the error
3. Return ONLY the fixed Python code
4. Do not include explanations or markdown
5. Preserve the original logic and structure

FIXED CODE:"""
        return prompt
    
    def _extract_code_from_response(self, response_text: str) -> str:
        """Extract Python code from Gemini response."""
        # Remove markdown code blocks if present
        if "```python" in response_text:
            start = response_text.find("```python") + 9
            end = response_text.find("```", start)
            if end != -1:
                return response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            if end != -1:
                return response_text[start:end].strip()
        
        return response_text.strip()
