"""
FastAPI Dependency Injection for Services.
Provides singleton instances with lazy loading.
Addresses Jules Code Review P1 - Dependency Injection.
"""

from functools import lru_cache
from typing import Optional
import os
from fastapi import HTTPException, Header, status
from autofix_core.application.services.debugger_service import DebuggerService
from autofix_core.application.services.tools_service import ToolsService
from autofix_core.infrastructure.ai_providers.gemini_provider import GeminiProvider
from autofix_core.application.services.gemini_service import GeminiService, AutoFixService, GEMINI_MODEL
from autofix_core.shared.helpers.logging_utils import get_logger

logger = get_logger(__name__)


# Singleton instances (lazy loaded)
_autofix_service: Optional[AutoFixService] = None
_gemini_service: Optional[GeminiService] = None
_debugger_service: Optional[DebuggerService] = None



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


@lru_cache()
def get_debugger_service() -> DebuggerService:
    """Get or create DebuggerService singleton."""
    global _debugger_service
    if _debugger_service is None:
        logger.info("Initializing DebuggerService")
        _debugger_service = DebuggerService()
        logger.info("✅ DebuggerService initialized")
    return _debugger_service


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

@lru_cache()
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
    global _autofix_service, _gemini_service, _debugger_service
    
    logger.info("Resetting all service singletons")
    
    # Clear cached functions
    get_tools_service.cache_clear()
    get_debugger_service.cache_clear()
    
    # Reset global instances
    _autofix_service = None
    _gemini_service = None
    _debugger_service = None
    
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


# ==================== Debug Auth Dependencies ====================
# Added for GitHub Copilot security review - Secure debug endpoints


def _env_flag_true(var_name: str) -> bool:
    """Check if environment variable is set to true."""
    v = os.getenv(var_name, "")
    return v.lower() in ("1", "true", "yes", "on")


def require_debug_enabled() -> None:
    """
    Dependency that checks if debug API is enabled.
    
    ⚠️ WARNING: Debug endpoints execute arbitrary Python code!
    NEVER expose these in production without proper auth!
    
    Required env var:
        DEBUG_API_ENABLED=true
    
    Raises:
        HTTPException: 403 if debug API is not enabled
        
    Example:
        @router.post("/endpoint", dependencies=[Depends(require_debug_enabled)])
    """
    if not _env_flag_true("DEBUG_API_ENABLED"):
        logger.warning("⚠️ Attempted access to debug API while disabled")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debug API is disabled. Set DEBUG_API_ENABLED=true to enable."
        )
    logger.debug("✅ Debug API enabled check passed")


def require_debug_api_key(
    x_debug_api_key: Optional[str] = Header(None, alias="X-Debug-API-Key")
) -> None:
    """
    Dependency that validates debug API key.
    
    Requires X-Debug-API-Key header with valid key.
    Fail-safe: denies access if key not configured.
    
    Required env var:
        DEBUG_API_KEY=<your-secret-key>
    
    Args:
        x_debug_api_key: API key from X-Debug-API-Key header
        
    Raises:
        HTTPException: 403 if key is missing, not configured, or invalid
        
    Example:
        @router.post("/endpoint", dependencies=[Depends(require_debug_api_key)])
        
    Usage:
        curl -H "X-Debug-API-Key: your-key" http://localhost:8000/api/v1/debug/execute
    """
    expected_key = os.getenv("DEBUG_API_KEY", "")
    
    # Fail-safe: require key to be configured
    if not expected_key:
        logger.error("❌ DEBUG_API_KEY not configured but debug API is enabled!")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debug API key not configured. Set DEBUG_API_KEY environment variable."
        )
    
    # Check if key was provided
    if not x_debug_api_key:
        logger.warning("⚠️ Debug API access attempted without API key")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Debug-API-Key header. Include API key in request."
        )
    
    # Verify key matches
    if x_debug_api_key != expected_key:
        logger.warning(f"⚠️ Invalid debug API key attempted (first 8 chars: {x_debug_api_key[:8]}...)")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    
    # Success - log for audit trail
    logger.info("✅ Debug API access granted with valid key")
