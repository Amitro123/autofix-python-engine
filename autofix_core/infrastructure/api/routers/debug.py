"""
Debug API Router - Direct debugger access endpoints
Provides low-level code execution and tracing capabilities
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from autofix_core.infrastructure.api.dependencies import get_debugger_service
from autofix_core.application.services.debugger_service import DebuggerService, ExecutionMode
from autofix.helpers.logging_utils import get_logger
from autofix_core.infrastructure.api.dependencies import (
    get_debugger_service,
    require_debug_enabled,
    require_debug_api_key
)


logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/debug", tags=["debug"], dependencies=[Depends(require_debug_enabled), Depends(require_debug_api_key)])

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
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    error_line: Optional[int] = None
    variables_at_error: Optional[Dict[str, Any]] = None
    variables_at_end: Optional[Dict[str, Any]] = None
    stack_trace: Optional[List[Dict[str, Any]]] = None
    execution_context: Optional[Dict[str, Any]] = None

# ==================== Endpoints ====================

@router.post("/execute", response_model=ExecuteResponse)
async def execute_code(
    request: ExecuteRequest,
    debugger: DebuggerService = Depends(get_debugger_service),
):
    """
    Execute Python code safely with RestrictedPython.

    Modes:
    - `simple`: Fast execution, minimal data
    - `traced`: Full context capture with variables
    """
    logger.info(f"📦 Execute request (mode={request.mode}, timeout={request.timeout}s)")
    try:
        # Pass explicit mode to debugger.execute
        result = debugger.execute(request.code, timeout=request.timeout)
        # Normalize result to expected ExecuteResponse fields
        resp = ExecuteResponse(
            success=result.success,  # ✅
            output=result.output,  # ✅
            error=result.error,  # ✅
            error_type=result.error_type,  # ✅
            variables=result.variables,  # ✅
            execution_time=result.execution_time,  # ✅
            timeout=result.timeout,  # ✅
        )

        return resp
    except Exception:
        # Log exception details internally but do not return internals to clients
        logger.exception("Execute error")
        raise HTTPException(status_code=500, detail="Internal server error while executing code")

@router.post("/trace", response_model=TraceResponse)
async def execute_with_trace(
    request: ExecuteRequest,
    debugger: DebuggerService = Depends(get_debugger_service),
):
    """
    Execute Python code with detailed tracing and context capture.
    """
    logger.info(f"📦 Trace request (timeout={request.timeout}s)")
    try:
        # Execute with tracing
        result = debugger.execute_with_trace(request.code, timeout=request.timeout)
        # Validate/normalize result before passing to Pydantic model
        normalized = {
            "success": bool(result.get("success", False)),
            "stdout": result.get("stdout"),
            "stderr": result.get("stderr"),
            "error_type": result.get("error_type"),
            "error_message": result.get("error_message"),
            "error_line": result.get("error_line"),
            "variables_at_error": result.get("variables_at_error"),
            "variables_at_end": result.get("variables_at_end"),
            "stack_trace": result.get("stack_trace"),
            "execution_context": result.get("execution_context"),
        }
        return TraceResponse(**normalized)
    except Exception:
        logger.exception("Trace error")
        raise HTTPException(status_code=500, detail="Internal server error while tracing code")

@router.get("/last-execution")
async def get_last_execution(
    debugger: DebuggerService = Depends(get_debugger_service),
):
    result = debugger.get_last_execution()
    if result is None:
        raise HTTPException(status_code=404, detail="No previous execution found")
    # Ensure we do not leak internal exception details
    return result

@router.delete("/last-execution")
async def clear_last_execution(
    debugger: DebuggerService = Depends(get_debugger_service),
):
    debugger.clear_last_execution()
    return {"message": "Last execution cleared"}

@router.get("/health")
async def debug_health(
    debugger: DebuggerService = Depends(get_debugger_service),
):
    return {
        "status": "healthy",
        "service": "DebuggerService",
        "features": {
            "sandboxed_execution": True,
            "timeout_protection": True,
            "variable_tracing": True,
            "modes": ["simple", "traced"],
        },
    }

@router.post("/track")
async def track_execution(
    request: ExecuteRequest,
    debugger_service: DebuggerService = Depends(get_debugger_service),
):
    """
    Execute code with detailed variable tracking.

    Returns:
    - Line-by-line variable snapshots
    - Variable change history
    - Visual timeline data
    """
    try:
        result = debugger_service.execute_with_tracking(code=request.code, timeout=request.timeout)
        # sanitize result before returning to avoid leaking internals
        # assume result contains a safe structure prepared by DebuggerService
        return result
    except Exception:
        logger.exception("Tracking error")
        return {"success": False, "error": "Internal error during tracking"}