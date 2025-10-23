"""
Fallback Service - Graceful degradation when AI fails
Handles errors when Gemini is unavailable or unknown errors occur
"""

from typing import Dict, Any, Optional
from autofix_core.shared.helpers.logging_utils import get_logger

logger = get_logger(__name__)


class FallbackService:
    """
    Handles fallback strategies when primary fixing methods fail
    
    Fallback order:
    1. Local patterns
    2. RAG memory
    3. Gemini AI
    4. Web search (Phase 2)
    5. Helpful error message
    """
    
    def __init__(
        self,
        local_engine=None,
        memory_service=None,
        web_search_service=None  # Phase 2!
    ):
        """Initialize with available services"""
        self.local_engine = local_engine
        self.memory_service = memory_service
        self.web_search = web_search_service
        
        logger.info("FallbackService initialized")
    
    def handle_gemini_failure(
        self,
        code: str,
        error_type: str,
        error_message: str,
        gemini_error: Exception
    ) -> Dict[str, Any]:
        """
        Handle case when Gemini API fails
        
        Args:
            code: Original broken code
            error_type: Type of error (IndexError, etc.)
            error_message: Error message
            gemini_error: The exception from Gemini
            
        Returns:
            Fallback fix result
        """
        logger.warning(f"Gemini unavailable: {gemini_error}")
        
        # Fallback 1: Try RAG memory
        if self.memory_service:
            logger.info("Fallback: Trying RAG memory search...")
            memory_result = self._try_memory_fallback(
                code, error_type, error_message
            )
            if memory_result['success']:
                return memory_result
        
        # Fallback 2: Try web search (Phase 2)
        if self.web_search:
            logger.info("Fallback: Trying web search...")
            web_result = self._try_web_fallback(
                code, error_type, error_message
            )
            if web_result['success']:
                return web_result
        
        # Fallback 3: Return helpful error message
        return self._generate_helpful_message(
            code, error_type, error_message, gemini_error
        )
    
    def _try_memory_fallback(
        self,
        code: str,
        error_type: str,
        error_message: str
    ) -> Dict[str, Any]:
        """Try to find similar fix in RAG memory"""
        try:
            if not self.memory_service:
                return {'success': False}
            
            # Search for similar errors
            results = self.memory_service.search_similar(
                query=f"{error_type}: {error_message}",
                error_type=error_type,
                k=3
            )
            
            if results and len(results) > 0:
                # Use top result
                best_match = results[0]
                
                logger.info(f"Found similar fix in memory (confidence: {best_match.get('score', 0):.2f})")
                
                return {
                    'success': True,
                    'fixed_code': best_match['fixed_code'],
                    'explanation': (
                        f"Found similar fix in memory:\n"
                        f"{best_match.get('explanation', 'Applied similar pattern')}"
                    ),
                    'method': 'memory_fallback',
                    'confidence': best_match.get('score', 0.5)
                }
            
            return {'success': False}
            
        except Exception as e:
            logger.error(f"Memory fallback failed: {e}")
            return {'success': False}
    
    def _try_web_fallback(
        self,
        code: str,
        error_type: str,
        error_message: str
    ) -> Dict[str, Any]:
        """Try to find solution via web search (Phase 2)"""
        try:
            if not self.web_search:
                return {'success': False}
            
            # Search StackOverflow, docs, etc.
            search_results = self.web_search.search(
                query=f"python {error_type} {error_message}",
                sources=['stackoverflow', 'python_docs']
            )
            
            if search_results['success']:
                return {
                    'success': True,
                    'fixed_code': search_results['suggested_fix'],
                    'explanation': search_results['explanation'],
                    'method': 'web_search_fallback',
                    'source': search_results['source_url']
                }
            
            return {'success': False}
            
        except Exception as e:
            logger.error(f"Web search fallback failed: {e}")
            return {'success': False}
    
    def _generate_helpful_message(
        self,
        code: str,
        error_type: str,
        error_message: str,
        gemini_error: Exception
    ) -> Dict[str, Any]:
        """Generate helpful message when all else fails"""
        
        # Analyze error to provide guidance
        suggestions = self._get_manual_suggestions(error_type)
        
        return {
            'success': False,
            'error': 'Unable to automatically fix this error',
            'reason': str(gemini_error),
            'error_type': error_type,
            'error_message': error_message,
            'suggestions': suggestions,
            'next_steps': [
                f"Search online: https://stackoverflow.com/search?q=python+{error_type}",
                "Check Python documentation for this error type",
                "Try fixing manually based on the error message",
                "Ask in Python community forums"
            ],
            'method': 'helpful_message',
            'can_retry': True  # User can try again later
        }
    
    def _get_manual_suggestions(self, error_type: str) -> list:
        """Get manual fixing suggestions based on error type"""
        suggestions_map = {
            'IndexError': [
                "Check if you're accessing an index that exists (0 to len-1)",
                "Use len(list) to verify list size before accessing",
                "Consider using list.get() or try/except for safe access"
            ],
            'TypeError': [
                "Check that you're using compatible types in operations",
                "Use type() to verify variable types",
                "Convert types explicitly: int(), str(), etc."
            ],
            'KeyError': [
                "Check if the key exists in the dictionary",
                "Use dict.get('key', default) for safe access",
                "Verify dictionary structure and available keys"
            ],
            'AttributeError': [
                "Check if the object has the attribute you're accessing",
                "Use dir(object) to see available attributes",
                "Verify object type matches expectations"
            ]
        }
        
        return suggestions_map.get(error_type, [
            "Review the error message carefully",
            "Check Python documentation for this error",
            "Search for similar errors online"
        ])

