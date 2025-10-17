"""
Abstract base classes for AutoFix architecture.
Defines interfaces for code execution and fixing strategies.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import time

@dataclass
class ExecutionResult:
    """Standardized result from code execution."""
    success: bool
    output: str = ""
    error: Optional[str] = None
    error_type: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    timeout: bool = False

@dataclass
class FixResult:
    """Standardized result from code fixing."""
    success: bool
    original_code: str
    fixed_code: str
    error_type: str = "Unknown"
    method: str = "unknown"  # 'gemini', 'fallback', 'cache', etc.
    cache_hit: bool = False
    changes: List[str] = field(default_factory=list)
    explanation: str = ""
    execution_time: float = 0.0
    iterations: int = 0


class CodeExecutor(ABC):
    """
    Abstract base class for code execution strategies.
    
    Implementers:
    - DebuggerService (RestrictedPython execution)
    - SimpleExecutor (basic exec)
    - SandboxExecutor (Docker/VM)
    """
    
    @abstractmethod
    def execute(self, code: str, timeout: int = 5) -> ExecutionResult:
        """
        Execute code safely with timeout.
        
        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds
            
        Returns:
            ExecutionResult with output and status
        """
        pass
    
    def validate_syntax(self, code: str) -> Dict[str, Any]:
        """
        Validate code syntax before execution.
        Common implementation for all executors.
        """
        import ast
        try:
            ast.parse(code)
            return {'valid': True, 'error': None}
        except SyntaxError as e:
            return {
                'valid': False,
                'error': str(e),
                'line': e.lineno,
                'offset': e.offset
            }


class CodeFixer(ABC):
    """
    Abstract base class for code fixing strategies.
    
    Implementers:
    - GeminiService (AI-powered)
    - FallbackService (rule-based)
    - CacheService (cached fixes)
    """
    
    @abstractmethod
    def fix_code(self, code: str, auto_install: bool = False) -> FixResult:
        """
        Attempt to fix the provided code.
        
        Args:
            code: Broken Python code
            auto_install: Whether to auto-install missing packages
            
        Returns:
            FixResult with fixed code and metadata
        """
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """
        Check if this fixer is currently available.
        
        Returns:
            True if fixer can be used, False otherwise
        """
        pass
    
    def _measure_time(self, func):
        """Decorator to measure execution time."""
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            result.execution_time = time.time() - start
            return result
        return wrapper


class ToolProvider(ABC):
    """
    Abstract base class for AI tool providers.
    
    Implementers:
    - ToolsService (Gemini tools)
    - LangChainTools (LangChain integration)
    """
    
    @abstractmethod
    def get_tool_declarations(self) -> List[Dict[str, Any]]:
        """Get tool definitions for AI model."""
        pass
    
    @abstractmethod
    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a specific tool by name."""
        pass
