"""
FastAPI Dependency Injection for Services.
Provides singleton instances with lazy loading.
Addresses Jules Code Review P1 - Dependency Injection.
"""

from functools import lru_cache
from typing import Optional
import os

from api.services.debugger_service import DebuggerService
from api.services.tools_service import ToolsService
from api.services.autofix_service import GeminiService, AutoFixService
from autofix.helpers.logging_utils import get_logger

logger = get_logger(__name__)


# Singleton instances (lazy loaded)
_autofix_service: Optional[GeminiService] = None
_gemini_service: Optional[GeminiService] = None


@lru_cache()
def get_tools_service() -> ToolsService:
    """
    Get or create ToolsService singleton.
    
    Returns:
        ToolsService: Singleton instance
    """
    logger.debug("Initializing ToolsService")
    # ToolsService parameters are optional (None by default)
    return ToolsService()

def get_debugger_service() -> DebuggerService:
    """Get or create DebuggerService singleton."""
    logger.info("Initializing DebuggerService")
    debugger = DebuggerService()
    logger.info("✅ DebuggerService initialized")
    return debugger

def get_autofix_service() -> Optional[GeminiService]:
    """
    Get or create AutoFixService singleton.
    
    Returns:
        GeminiService or None: Service instance or None if initialization fails
        
    Note:
        Returns None gracefully if Gemini API is not configured or fails.
        This allows the API to start even without Gemini credentials.
    """
    global _autofix_service
    
    if _autofix_service is None:
        # Check if API key is available
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            logger.warning("GEMINI_API_KEY not set - AutoFixService will be unavailable")
            return None
        
        try:
            logger.info("Initializing AutoFixService")
            tools = get_tools_service()
            _autofix_service = AutoFixService(tools_service=tools)
            logger.info("✅ AutoFixService initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize AutoFixService: {e}", exc_info=True)
            logger.warning("AutoFixService disabled - returning None")
            return None
    
    return _autofix_service


def get_gemini_service() -> Optional[GeminiService]:
    """
    Get or create GeminiService singleton.
    
    Returns:
        GeminiService or None: Service instance or None if initialization fails
    """
    global _gemini_service
    
    if _gemini_service is None:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            logger.warning("GEMINI_API_KEY not set - GeminiService will be unavailable")
            return None
        
        try:
            logger.info("Initializing GeminiService")
            tools = get_tools_service()
            _gemini_service = GeminiService(tools_service=tools)
            logger.info("✅ GeminiService initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize GeminiService: {e}", exc_info=True)
            logger.warning("GeminiService disabled - returning None")
            return None
    
    return _gemini_service


def reset_services():
    """
    Reset all service singletons.
    Useful for testing and reloading.
    """
    global _autofix_service, _gemini_service
    
    logger.info("Resetting all service singletons")
    
    # Clear cached functions
    get_tools_service.cache_clear()
    
    # Reset global instances
    _autofix_service = None
    _gemini_service = None
    
    logger.info("All services reset")

@lru_cache()
def get_firestore_client():
    """
    Get or create Firestore client singleton.
    
    Returns:
        Firestore client if available, None otherwise.
    """
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        
        # Check if Firebase app already initialized
        try:
            app = firebase_admin.get_app()
            logger.debug("Using existing Firebase app")
        except ValueError:
            # Initialize Firebase app
            logger.info("Initializing Firebase app...")
            
            # Try to load credentials
            try:
                cred = credentials.Certificate("path/to/serviceAccountKey.json")
                firebase_admin.initialize_app(cred)
                logger.info("✅ Firebase initialized with service account")
            except Exception as e:
                # Fallback to default credentials
                logger.warning(f"Service account not found, using default: {e}")
                firebase_admin.initialize_app()
                logger.info("✅ Firebase initialized with default credentials")
        
        # Get Firestore client
        client = firestore.client()
        logger.info("✅ Firestore client ready")
        return client
        
    except ImportError:
        logger.warning("⚠️ Firebase Admin SDK not installed")
        return None
    except Exception as e:
        logger.error(f"❌ Failed to initialize Firestore: {e}", exc_info=True)
        return None
