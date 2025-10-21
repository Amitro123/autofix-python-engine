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
import datetime


router = APIRouter(prefix="/api/v1/quality", tags=["code-quality"])
tools_service = ToolsService()


class CodeAnalysisRequest(BaseModel):
    """Request model for code analysis."""
    code: str = Field(
        ..., 
        description="Python code to analyze",
        min_length=1,
        max_length=100000
    )
    filename: Optional[str] = Field(
        None, 
        description="Optional filename for context"
    )



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
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Bandit is not installed",
                "hint": "Install with: pip install bandit",
                "docs": "https://bandit.readthedocs.io/"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": f"Security analysis failed: {str(e)}",
                "hint": "Check if code is valid Python syntax"
            }
        )


@router.post(
    "/complexity",
    response_model=ComplexityAnalysisResponse,
    summary="Complexity Analysis",
    description="Analyze code complexity and maintainability using Radon"
)
async def analyze_complexity(request: CodeAnalysisRequest):
    """..."""
    try:
        result = tools_service.analyze_complexity(request.code)
        return ComplexityAnalysisResponse(**result)
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Radon is not installed",
                "hint": "Install with: pip install radon",
                "docs": "https://radon.readthedocs.io/"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": f"Complexity analysis failed: {str(e)}",
                "hint": "Check if code is valid Python syntax"
            }
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

@router.get(
    "/health",
    summary="Health Check",
    description="Check availability of quality analysis tools"
)

async def quality_health():
    """
    Check health status of quality analyzers.
    
    Returns availability status for:
    - Bandit (security scanner)
    - Radon (complexity analyzer)
    
    Useful for monitoring and service health checks.
    """
    import importlib.util
    
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "analyzers": {
            "bandit": {
                "available": importlib.util.find_spec("bandit") is not None,
                "type": "security",
                "checks": 30 if importlib.util.find_spec("bandit") else 0
            },
            "radon": {
                "available": importlib.util.find_spec("radon") is not None,
                "type": "complexity",
                "metrics": ["MI", "CC", "Halstead"] if importlib.util.find_spec("radon") else []
            }
        },
        "api_version": "2.7.0"
    }


@router.get(
    "/stats",
    summary="Analysis Statistics",
    description="Get statistics about available analysis capabilities"
)
async def quality_stats():
    """
    Get detailed statistics about quality analysis capabilities.
    
    Returns:
    - Number of available analyzers
    - Total security checks
    - Total complexity metrics
    - Supported Python versions
    """
    import sys
    import importlib.util
    
    has_bandit = importlib.util.find_spec("bandit") is not None
    has_radon = importlib.util.find_spec("radon") is not None
    
    return {
        "analyzers": {
            "total": 3,  # pylint, bandit, radon
            "code_quality": 1,  # pylint
            "security": 1 if has_bandit else 0,
            "complexity": 1 if has_radon else 0
        },
        "capabilities": {
            "security_checks": 30 if has_bandit else 0,
            "security_categories": [
                "hardcoded_secrets",
                "sql_injection",
                "command_injection",
                "insecure_functions",
                "ssl_tls",
                "weak_crypto"
            ] if has_bandit else [],
            "complexity_metrics": [
                "maintainability_index",
                "cyclomatic_complexity",
                "halstead_volume",
                "halstead_difficulty"
            ] if has_radon else [],
            "grade_scale": "A (excellent) to F (poor)" if has_radon else None
        },
        "environment": {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": sys.platform
        }
    }

