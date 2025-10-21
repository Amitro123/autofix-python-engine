"""
Quality analysis endpoints for security scanning and complexity metrics.

Provides:
- POST /api/v1/quality/security - Bandit security scanner
- POST /api/v1/quality/complexity - Radon complexity analyzer
- GET /api/v1/quality/analyzers - List available analyzers
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from api.services.tools_service import ToolsService

router = APIRouter(prefix="/api/v1/quality", tags=["code-quality"])
tools_service = ToolsService()


class CodeAnalysisRequest(BaseModel):
    """Request model for code analysis."""
    code: str = Field(..., description="Python code to analyze")
    filename: Optional[str] = Field(None, description="Optional filename for context")


class SecurityAnalysisResponse(BaseModel):
    """Response from security analysis."""
    analyzer: str
    total_issues: int
    severity_counts: dict
    issues: list[dict]
    timestamp: str


class ComplexityAnalysisResponse(BaseModel):
    """Response from complexity analysis."""
    analyzer: str
    maintainability_index: Optional[float]
    grade: Optional[str]
    complexity_issues: int
    issues: list[dict]
    timestamp: str


@router.post(
    "/security",
    response_model=SecurityAnalysisResponse,
    summary="Security Analysis",
    description="Scan Python code for security vulnerabilities using Bandit"
)
async def analyze_security(request: CodeAnalysisRequest):
    """
    Run Bandit security scanner on Python code.
    
    Detects 30+ security issues including:
    - Hardcoded passwords and secrets (B105, B106, B107)
    - SQL injection vulnerabilities (B608)
    - Command injection risks (B602, B605, B607)
    - Use of eval/exec (B307)
    - Insecure deserialization (B301, B302, B303)
    - SSL/TLS issues (B501, B502, B503)
    - Path traversal risks (B108)
    - Weak cryptography (B303, B304, B305)
    
    Example:
        ```
        POST /api/v1/quality/security
        {
            "code": "import os\\npassword = 'secret123'\\nos.system('ls')"
        }
        ```
    
    Returns:
        SecurityAnalysisResponse with detected issues and severity counts
    """
    try:
        result = tools_service.analyze_security(request.code)
        return SecurityAnalysisResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Security analysis failed: {str(e)}"
        )


@router.post(
    "/complexity",
    response_model=ComplexityAnalysisResponse,
    summary="Complexity Analysis",
    description="Analyze code complexity and maintainability using Radon"
)
async def analyze_complexity(request: CodeAnalysisRequest):
    """
    Run Radon complexity analyzer on Python code.
    
    Computes:
    - Maintainability Index (MI): 0-100 scale
      * 100-20: Grade A (excellent)
      * 20-10: Grade B (good)
      * 10-0: Grade C (acceptable)
      * < 0: Grade F (poor)
    
    - Cyclomatic Complexity (CC) per function:
      * CC 1-10: Simple, easy to test
      * CC 11-15: Moderate complexity (WARNING)
      * CC 16-20: High complexity (ERROR)
      * CC > 20: Very high complexity (CRITICAL)
    
    Example:
        ```
        POST /api/v1/quality/complexity
        {
            "code": "def complex_function(a, b, c):\\n    if a:\\n        if b:\\n            return c"
        }
        ```
    
    Returns:
        ComplexityAnalysisResponse with MI score, grade, and complexity issues
    """
    try:
        result = tools_service.analyze_complexity(request.code)
        return ComplexityAnalysisResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Complexity analysis failed: {str(e)}"
        )


@router.get(
    "/analyzers",
    summary="List Analyzers",
    description="Get list of all available code quality analyzers"
)
async def list_analyzers():
    """
    List all available code quality analyzers.
    
    Returns information about:
    - Analyzer name and type
    - API endpoint
    - Description
    - Supported features
    
    Returns:
        dict with list of available analyzers and their details
    """
    return {
        "analyzers": [
            {
                "name": "pylint",
                "type": "code_quality",
                "endpoint": "/api/v1/tools/analyze",
                "description": "Static code analysis for code quality issues",
                "features": ["style", "errors", "refactoring", "convention"]
            },
            {
                "name": "bandit",
                "type": "security",
                "endpoint": "/api/v1/quality/security",
                "description": "Security vulnerability scanner",
                "features": [
                    "hardcoded_secrets",
                    "sql_injection",
                    "command_injection",
                    "insecure_functions",
                    "ssl_tls",
                    "weak_crypto"
                ],
                "checks_count": 30
            },
            {
                "name": "radon",
                "type": "complexity",
                "endpoint": "/api/v1/quality/complexity",
                "description": "Code complexity and maintainability metrics",
                "features": [
                    "maintainability_index",
                    "cyclomatic_complexity",
                    "halstead_metrics"
                ],
                "grade_scale": "A (best) to F (worst)"
            }
        ],
        "total_analyzers": 3
    }
