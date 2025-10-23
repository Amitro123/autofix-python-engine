from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from autofix_core.application.services.gemini_service import GeminiService, AutoFixService, GEMINI_MODEL
from autofix_core.infrastructure.ai_providers.gemini_provider import GeminiProvider
from autofix_core.application.services.tools_service import ToolsService
from autofix.helpers.logging_utils import get_logger
import time
from typing import List, Optional
import subprocess
import tempfile
import sys
import os
from autofix_core.infrastructure.api.dependencies import (
    get_autofix_service,
    get_gemini_service,
    get_firestore_client,
    get_tools_service,
    get_debugger_service,
    get_gemini_service
)


router = APIRouter(
    prefix="/api/v1",
    tags=["fix"]
)

logger = get_logger(__name__)





class FixRequest(BaseModel):
    code: str
    error: str = "Unknown"
    auto_install: bool = False


class FixResponse(BaseModel):
    success: bool
    original_code: str
    fixed_code: str | None = None
    error_type: str
    method: str
    cache_hit: bool = False
    changes: list = []
    execution_time: float


class ValidateRequest(BaseModel):
    code: str

@router.post("/validate")
async def validate_code(request: ValidateRequest):
    """
    ✅ Check if code has errors (without fixing)
    
    Security:
    - Adds timeout to prevent DoS attacks (Jules P0 fix)
    - Properly handles timeout exceptions
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(request.code)
        temp_file = f.name
    
    try:
        # FIX: Add timeout to prevent resource exhaustion
        result = subprocess.run(
            [sys.executable, '-m', 'py_compile', temp_file],
            capture_output=True,
            text=True,
            timeout=5  # 5 second timeout (Jules P0 critical fix)
        )
        
        return {
            "valid": result.returncode == 0,
            "error": result.stderr if result.returncode != 0 else None
        }
    
    except subprocess.TimeoutExpired:
        # FIX: Handle timeout gracefully
        logger = get_logger(__name__)
        logger.warning(f"Validation timeout for code: {request.code[:50]}...")
        return {
            "valid": False,
            "error": "Validation timeout - code compilation took too long (>5s)"
        }
    
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


@router.post("/fix")
async def fix_code(
    request: FixRequest,
    autofix_service: GeminiProvider = Depends(get_autofix_service)
):
    """
    🔧 Fix Python code using Hybrid AI approach
    
    Uses FastAPI dependency injection for service management.
    """
    start_time = time.time()
    
    # Check if service is available
    if autofix_service is None:
        logger.warning("AutoFix service unavailable - check GEMINI_API_KEY")
        raise HTTPException(
            status_code=503,
            detail="AutoFix service is temporarily unavailable. Please check configuration."
        )
    
    try:
        logger.info(f"📥 Received fix request")
        
        # Call service
        result = autofix_service.fix_code(
            code=request.code,
            auto_install=getattr(request, 'auto_install', False)
        )

        
        # Log result
        execution_time = time.time() - start_time
        
        if result.get('success'):
            method = result.get('method', 'unknown')
            cache_hit = result.get('cache_hit', False)
            
            if method == 'autofix':
                logger.success(f"✅ AutoFix succeeded in {execution_time:.3f}s")
            elif cache_hit:
                logger.success(f"⚡ Cache HIT! Retrieved in {execution_time:.3f}s")
            elif method == 'gemini':
                logger.success(f"🤖 Gemini fixed it in {execution_time:.3f}s")
        else:
            logger.error(f"❌ Fix failed in {execution_time:.3f}s")
        
        return result
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"💥 Error in fix_code endpoint: {str(e)}")
        
        return {
            "success": False,
            "original_code": request.code,
            "fixed_code": None,
            "error_type": "InternalError",
            "method": "error",
            "cache_hit": False,
            "changes": [],
            "execution_time": execution_time,
            "error_message": str(e)
        }


@router.post("/fix-batch", response_model=List[FixResponse])
async def fix_batch(requests: List[FixRequest], autofix_service: Optional[GeminiService] = Depends(get_autofix_service)):
    """
    🔧 Fix multiple code snippets at once
    
    **Example:**
    ```
    [
      {"code": "if True\\n    print('hello')", "auto_install": false},
      {"code": "def test()\\nprint('world')", "auto_install": false}
    ]
    ```
    """
    results = []
    
    for req in requests:
        start = time.time()
        try:
            result = autofix_service.fix_code(
                code=req.code,
                auto_install=req.auto_install
            )
            result["execution_time"] = round(time.time() - start, 3)
            results.append(result)
        except Exception as e:
            results.append({
                "success": False,
                "original_code": req.code,
                "fixed_code": None,
                "error_type": str(type(e).__name__),
                "method": "error",
                "changes": [],
                "execution_time": round(time.time() - start, 3)
            })
    
    return results
    

@router.get("/errors") #import from constants
async def supported_errors():
    """📋 Get supported error types"""
    return {
        "errors": [
            "SyntaxError",
            "IndentationError", 
            "ModuleNotFoundError",
            "TypeError",
            "IndexError",
            "NameError",
            "AttributeError",
            "ZeroDivisionError",
            "KeyError",
            "FileNotFoundError",
            "ValueError",
            "importError"
        ],
        "total_count": 12,
        "new_in_v2_2_0": [
            "FileNotFoundError",
            "ValueError"
        ]
    }


@router.get("/stats")
async def get_stats(
    gemini_service: Optional[GeminiService] = Depends(get_gemini_service)
):
    """📊 Get comprehensive API statistics"""
    
    # Check if Gemini is enabled
    gemini_enabled = False
    gemini_model = None
    
    if gemini_service is not None:
        try:
            gemini_enabled = gemini_service.is_enabled()
            gemini_model = GEMINI_MODEL if gemini_enabled else None
        except (AttributeError, RuntimeError) as e:
            logger.warning(f"Failed to check Gemini status: {e}")
            gemini_enabled = False
        except Exception as e:
            logger.error(f"Unexpected error checking Gemini: {e}", exc_info=True)
            gemini_enabled = False
    
    # Initialize Firebase variables
    firebase_enabled = False
    total_fixes_from_db = 0
    
    # Try to get Firebase metrics (optional)
    try:
        from autofix.integrations.firestore_client import get_firestore_client
        client = get_firestore_client()
        
        if client:
            firebase_enabled = True
            metrics_ref = client.collection('autofix_metrics')
            total_fixes_from_db = len(list(metrics_ref.stream()))
            logger.debug(f"Retrieved {total_fixes_from_db} metrics from Firebase")
    except ImportError as e:
        logger.debug(f"Firebase client not available: {e}")
    except (AttributeError, ValueError, RuntimeError) as e:
        logger.warning(f"Firebase operation failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error accessing Firebase: {e}", exc_info=True)
    
    return {
        "api_version": "2.4.0",
        "autofix_version": "1.0.0",
        "gemini_enabled": gemini_enabled,
        "gemini_model": gemini_model,
        "gemini_free_tier": True if gemini_enabled else None,
        "firebase_enabled": firebase_enabled,
        "total_fixes": total_fixes_from_db,
        "success_rate": 0.95,
        "avg_execution_time": 0.5,
        "supported_errors": 12,
        "endpoints": {
            "fix": "/api/v1/fix",
            "batch": "/api/v1/fix-batch",
            "validate": "/api/v1/validate",
            "errors": "/api/v1/errors",
            "firebase": "/api/v1/firebase-status",
            "metrics": "/api/v1/firebase-metrics",
            "stats": "/api/v1/stats"
        }
    }

@router.get("/firebase-status")
async def check_firebase():
    """
    🔥 Check Firebase connection status
    
    Tests:
    - Firebase credentials
    - Firestore connection
    - Read/Write permissions
    """
    try:
        # Import Firebase client        
        from autofix.integrations.firestore_client import get_firestore_client
        # Try to get client
        client = get_firestore_client()
        
        if client is None:
            return {
                "status": "disabled",
                "message": "Firebase is not configured",
                "credentials": False,
                "connection": False,
                "permissions": None
            }
        
        # Test connection by reading a test document
        try:
            # Try to access a collection (won't create if doesn't exist)
            test_ref = client.collection('_health_check').document('test')
            
            # Try to write
            test_ref.set({
                'timestamp': time.time(),
                'test': 'API health check'
            })
            
            # Try to read
            doc = test_ref.get()
            can_read = doc.exists
            
            # Clean up
            test_ref.delete()
            
            return {
                "status": "connected",
                "message": "Firebase is working correctly",
                "credentials": True,
                "connection": True,
                "permissions": {
                    "read": can_read,
                    "write": True,
                    "delete": True
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Firebase connection failed: {str(e)}",
                "credentials": True,
                "connection": False,
                "permissions": None,
                "error": str(e)
            }
            
    except ImportError:
        return {
            "status": "not_installed",
            "message": "Firebase dependencies not installed",
            "credentials": False,
            "connection": False,
            "permissions": None
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "credentials": False,
            "connection": False,
            "permissions": None,
            "error": str(e)
        }


@router.get("/firebase-metrics")
async def get_firebase_metrics():
    """
    📊 Get recent metrics from Firebase
    
    Returns latest 10 fix operations stored in Firestore
    """
    try:
        from autofix.integrations.firestore_client import get_firestore_client
        
        client = get_firestore_client()
        
        if client is None:
            return {
                "status": "disabled",
                "metrics": []
            }
        
        # Get recent metrics
        metrics_ref = client.collection('autofix_metrics') \
                           .order_by('timestamp', direction='DESCENDING') \
                           .limit(10)
        
        docs = metrics_ref.stream()
        
        metrics = []
        for doc in docs:
            data = doc.to_dict()
            metrics.append({
                "id": doc.id,
                "error_type": data.get('error_type'),
                "success": data.get('success'),
                "timestamp": data.get('timestamp'),
                "app_id": data.get('app_id')
            })
        
        return {
            "status": "success",
            "count": len(metrics),
            "metrics": metrics
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "metrics": []
        }


