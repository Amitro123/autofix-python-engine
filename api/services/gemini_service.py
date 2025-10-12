"""Google Gemini AI Service for AutoFix"""
import os
from typing import Optional
from .gemini_cache import GeminiCache, GeminiCacheConfig
from autofix.helpers.logging_utils import get_logger
from autofix.integrations.metrics_collector import record_cache_stats

logger = get_logger(__name__)


try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class GeminiService:
    """Service to integrate Gemini AI for code fixing"""
    
    def __init__(self):
        """Initialize Gemini with API key"""
        if not GENAI_AVAILABLE:
            self.enabled = False
            return
            
        api_key = os.getenv("GEMINI_API_KEY")
        
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            self.enabled = True

            # Jules: Configure cache *after* model is available
            # This allows passing the model name for versioning
            cache_config = GeminiCacheConfig()
            cache_config.MODEL_NAME = self.model.model_name
            self.cache = GeminiCache(cache_config)

        else:
            self.enabled = False
            self.cache = None

    def fix_with_ai(self, code: str, error: str) -> Optional[str]:
        """
        Use Gemini to fix Python code with caching and token counting
        
        v2.2.1 improvements based on Jules' recommendations:
        - Check cache first (faster, cheaper)
        - Use accurate token counting (model.count_tokens)
        - Cache successful results
        - Better error handling
        """
        if not self.enabled:
            logger.info("Gemini disabled, skipping AI fix")
            return None
        
        logger.attempt("Starting AI fix process")
        
        # Step 1: Check cache first (Jules: huge performance win!)
        if self.cache:
            cached_result = self.cache.get(code, error)
            if cached_result:
                logger.success("🎯 Cache HIT! Returning cached fix")
                # Log cache stats to Firebase
                record_cache_stats(self.cache.get_stats())
                # Cache stores dict, extract fixed_code
                return cached_result.get('fixed_code')
            logger.attempt("Cache MISS - calling Gemini API")
        
        # Step 2: Accurate token counting (Jules: use model.count_tokens!)
        try:
            token_count = self._count_tokens(code, error)
            logger.info(f"Token count: {token_count}")
            
            if token_count > 30000:  # Gemini 2.0 Flash limit
                logger.warning(f"Input too large: {token_count} tokens (max: 30000)")
                return None
        except Exception as e:
            logger.warning(f"Token counting failed: {e}, proceeding anyway")
        
        # Step 3: Call Gemini API with improved prompt
        try:
            prompt = "You are an expert Python debugger.\n\n"
            prompt += f"Error:\n{error}\n\n"
            prompt += f"Code:\n```python\n{code}\n```\n\n"
            prompt += "Provide ONLY the fixed code, no explanations."
            
            logger.attempt("Calling Gemini API...")
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.1,  # Low for consistency
                    'top_p': 0.95,
                    'top_k': 40,
                    'max_output_tokens': 8192,
                }
            )
            
            if not response or not response.text:
                logger.error("Empty response from Gemini")
                return None
            
            fixed_code = self._clean_response(response.text)
            
            # Step 4: Cache successful fix (Jules: cache for efficiency!)
            if self.cache and fixed_code:
                # Create result dict for cache
                result = {
                    'fixed_code': fixed_code,
                    'confidence': 0.8,  # Default confidence
                    'error_type': error.split(':')[0] if ':' in error else 'Error',
                    'ai_used': True,
                    'cached': False
                }
                self.cache.set(code, error, result)
                logger.success("💾 Cached successful fix")
            
            logger.success("✅ Gemini fix successful")
            return fixed_code
            
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return None

    
    def _clean_response(self, text: str) -> str:
        """Extract Python code from Gemini response - remove markdown"""
        if not text:
            return ""
        
        text = text.strip()
        text = text.replace('```python', '')
        text = text.replace('```', '')
        
        if text.startswith('python\n'):
            text = text[7:]
        elif text.startswith('python'):
            text = text[6:]
        
        return text.strip()
    
    def _count_tokens(self, code: str, error_message: str) -> int:
        """
        Count tokens accurately using Gemini's official counter
        
        Jules' recommendation: Use model.count_tokens() for accuracy
        - Exact token count (not estimation)
        - Fast and lightweight
        - Prevents InvalidRequestError
        """
        try:
            # Build the actual prompt we'll send
            prompt = "You are an expert Python debugger.\n\n"
            prompt += f"Error:\n{error_message}\n\n"
            prompt += f"Code:\n```python\n{code}\n```\n\n"
            prompt += "Provide ONLY the fixed code, no explanations."
            
            # Jules: This is fast and lightweight!
            token_result = self.model.count_tokens(prompt)
            
            return token_result.total_tokens
            
        except Exception as e:
            # Fallback to estimation if counting fails
            logger.warning(f"Token counting failed: {e}, using estimation")
            total_text = code + error_message
            estimated = int(len(total_text.split()) * 1.3)
            return estimated


    def is_enabled(self) -> bool:
        """Check if Gemini is configured"""
        return self.enabled