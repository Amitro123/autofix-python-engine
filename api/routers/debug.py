"""
Debug API Router - Direct debugger access endpoints
Provides low-level code execution and tracing capabilities
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from api.dependencies import get_debugger_service
from api.services.debugger_service import DebuggerService, ExecutionMode
from autofix.helpers.logging_utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/debug", tags=["debug"])


# ==================== Request/Response Models ====================

class ExecuteRequest(BaseModel):
    """Request model for code execution."""
    code: str = Field(..., description="Python code to execute")
    timeout: int = Field(5, ge=1, le=30, description="Timeout in seconds (1-30)")
    mode: str = Field("simple", description="Execution mode: 'simple' or 'traced'")


class ExecuteResponse(BaseModel):
    """Response model for code execution."""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    timeout: bool = False


class TraceResponse(BaseModel):
    """Response model for traced execution."""
    success: bool
    stdout: str
    stderr: str
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_line: Optional[int] = None
    variables_at_error: Dict[str, Any]
    variables_at_end: Optional[Dict[str, Any]] = None
    stack_trace: list
    execution_context: Dict[str, Any]


# ==================== Endpoints ====================

@router.post("/execute", response_model=ExecuteResponse)
async def execute_code(
    request: ExecuteRequest,
    debugger: DebuggerService = Depends(get_debugger_service)
):
    """
    Execute Python code safely with RestrictedPython.
    
    **Features:**
    - Sandboxed execution (no file I/O, no network)
    - Timeout protection
    - Variable capture
    - Output capture
    
    **Modes:**
    - `simple`: Fast execution, minimal data
    - `traced`: Full context capture with variables
    """
    logger.info(f"📥 Execute request (mode={request.mode}, timeout={request.timeout}s)")
    
    try:
        result = debugger.execute(request.code, timeout=request.timeout)
        
        return ExecuteResponse(
            success=result.success,
            output=result.output,
            error=result.error,
            error_type=result.error_type,
            variables=result.variables,
            execution_time=result.execution_time,
            timeout=result.timeout
        )
    
    except Exception as e:
        logger.error(f"💥 Execute error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trace", response_model=TraceResponse)
async def execute_with_trace(
    request: ExecuteRequest,
    debugger: DebuggerService = Depends(get_debugger_service)
):
    """
    Execute Python code with detailed tracing and context capture.
    
    **Returns:**
    - Full variable state at error point
    - Stack trace with code context
    - Execution context analysis
    - Line-by-line variable evolution (if error)
    
    **Use Cases:**
    - Deep debugging
    - Error analysis
    - Variable inspection
    - AI-powered code fixing
    """
    logger.info(f"📥 Trace request (timeout={request.timeout}s)")
    
    try:
        # Execute with tracing
        result = debugger.execute_with_trace(request.code, timeout=request.timeout)
        
        return TraceResponse(**result)
    
    except Exception as e:
        logger.error(f"💥 Trace error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/last-execution")
async def get_last_execution(
    debugger: DebuggerService = Depends(get_debugger_service)
):
    """
    Get the last traced execution result.
    
    **Use Case:** Retrieve detailed context from previous execution.
    """
    result = debugger.get_last_execution()
    
    if result is None:
        raise HTTPException(status_code=404, detail="No previous execution found")
    
    return result


@router.delete("/last-execution")
async def clear_last_execution(
    debugger: DebuggerService = Depends(get_debugger_service)
):
    """Clear the cached last execution."""
    debugger.clear_last_execution()
    return {"message": "Last execution cleared"}


@router.get("/health")
async def debug_health(
    debugger: DebuggerService = Depends(get_debugger_service)
):
    """Check debugger service health."""
    return {
        "status": "healthy",
        "service": "DebuggerService",
        "features": {
            "sandboxed_execution": True,
            "timeout_protection": True,
            "variable_tracing": True,
            "modes": ["simple", "traced"]
        }
    }

@router.post("/track")
async def track_execution(
    request: ExecuteRequest,
    debugger_service: DebuggerService = Depends(get_debugger_service)
):
    """
    Execute code with detailed variable tracking.
    
    Returns:
    - Line-by-line variable snapshots
    - Variable change history
    - Visual timeline data
    
    Example:
    ```
    POST /api/v1/debug/track
    {
        "code": "x = 10\\nx = x + 5\\nprint(x)"
    }
    
    Response:
    {
        "success": true,
        "tracking": {
            "snapshots": [
                {"line": 1, "variable": "x", "value": "10"},
                {"line": 2, "variable": "x", "value": "15"}
            ],
            "changes": [
                {"line": 2, "variable": "x", "old": "10", "new": "15"}
            ]
        }
    }
    ```
    """
    try:
        result = debugger_service.execute_with_tracking(
            code=request.code,
            timeout=request.timeout
        )
        return result
    
    except Exception as e:
        logger.error(f"Tracking error: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }

    