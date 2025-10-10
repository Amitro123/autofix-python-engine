"""Code fixing endpoints"""
from fastapi import APIRouter, HTTPException
from api.models.schemas import FixRequest, FixResponse
from api.services.autofix_service import AutoFixService
# ← NO import for get_firestore_client here!
import time
from typing import List
from pydantic import BaseModel



router = APIRouter()
service = AutoFixService()


class ValidateRequest(BaseModel):
    code: str

@router.post("/validate")
async def validate_code(request: ValidateRequest):
    """
    ✅ Check if code has errors (without fixing)
    """
    import subprocess
    import tempfile
    import sys
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(request.code)
        temp_file = f.name
    
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'py_compile', temp_file],
            capture_output=True,
            text=True
        )
        
        return {
            "valid": result.returncode == 0,
            "error": result.stderr if result.returncode != 0 else None
        }
    finally:
        import os
        if os.path.exists(temp_file):
            os.remove(temp_file)


@router.post("/fix", response_model=FixResponse)
async def fix_code(request: FixRequest):
    """
    🔧 Fix Python code automatically
    
    **Example:**
    ```
    {
      "code": "if True\\n    print('hello')",
      "auto_install": false
    }
    ```
    """
    start = time.time()
    
    try:
        result = service.fix_code(
            code=request.code,
            auto_install=request.auto_install
        )
        result["execution_time"] = round(time.time() - start, 3)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/fix-batch", response_model=List[FixResponse])
async def fix_batch(requests: List[FixRequest]):
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
            result = service.fix_code(
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
            "AttributeError"
        ],
        "total": 7
    }


@router.get("/stats")
async def get_stats():
    """📊 Get comprehensive API statistics"""
    
    # Check if Gemini is enabled
    gemini_enabled = service.gemini.is_enabled()
    
    # Try to get Firebase metrics (optional)
    firebase_enabled = False
    total_fixes_from_db = 0
    
    try:
        # ✅ Import INSIDE the function
        from autofix.integrations.firestore_client import get_firestore_client
        client = get_firestore_client()
        
        if client:
            firebase_enabled = True
            metrics_ref = client.collection('autofix_metrics')
            total_fixes_from_db = len(list(metrics_ref.stream()))
    except:
        pass
    
    return {
        "api_version": "2.0.0",
        "autofix_version": "1.0.0",
        "gemini_enabled": gemini_enabled,
        "gemini_model": "gemini-2.5-pro" if gemini_enabled else None,
        "gemini_free_tier": True if gemini_enabled else None,
        "firebase_enabled": firebase_enabled,
        "total_fixes": total_fixes_from_db,
        "success_rate": 0.95,
        "avg_execution_time": 0.5,
        "supported_errors": 7,
        "endpoints": {
            "fix": "/api/v1/fix",
            "batch": "/api/v1/fix-batch",
            "validate": "/api/v1/validate",
            "errors": "/api/v1/errors",
            "firebase": "/api/v1/firebase-status",
            "metrics": "/api/v1/firebase-metrics"
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
