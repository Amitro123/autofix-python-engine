"""
Tools Service for Gemini Function Calling
Provides executable tools for AI-powered debugging
"""

import subprocess
import tempfile
import os
import ast
import sys
import json
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from autofix.helpers.logging_utils import get_logger
from .sandbox_executor import SandboxExecutor
from .memory_service import MemoryService
from .debugger_service import DebuggerService




logger = get_logger(__name__)


class ToolsService:
    """Service providing tools for Gemini Function Calling"""
    
    def __init__(
    self,
    memory_service: MemoryService = None,
    sandbox_executor: SandboxExecutor = None,
    debugger_service: DebuggerService = None
    ):

        """
        Initialize tools service
        
        Args:
            memory_service: Optional MemoryService for RAG integration
        """
 

        self.memory_service = memory_service
        self.sandbox = sandbox_executor or SandboxExecutor()
        self.debugger = debugger_service or DebuggerService()
        self.execution_timeout = 5  # seconds
        self.max_output_size = 10000  # characters
    
    # ==================== TOOL 1: Execute Code ====================
    
    def execute_code(self, code: str, timeout: int = None) -> Dict[str, Any]:
        """
        Execute Python code safely in sandbox
        
        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds
            
        Returns:
            Dict with success, stdout, stderr, exit_code
        """
        return self.sandbox.execute_code(code, timeout)
    
    # ==================== TOOL 2: Validate Syntax ====================
    
    def validate_syntax(self, code: str) -> Dict[str, Any]:
        """
        Validate Python syntax without execution
        
        Args:
            code: Python code to validate
            
        Returns:
            Dict with:
                - valid: bool
                - message: str
                - error: str (if invalid)
                - line: int (error line number)
                - offset: int (error column)
                - text: str (line with error)
        """
        try:
            logger.info("Validating code syntax")
            
            # Try to parse as AST
            ast.parse(code)
            
            return {
                "valid": True,
                "message": "Syntax is valid"
            }
            
        except SyntaxError as e:
            logger.warning(f"Syntax error at line {e.lineno}: {e.msg}")
            
            return {
                "valid": False,
                "error": e.msg,
                "line": e.lineno,
                "offset": e.offset,
                "text": e.text.strip() if e.text else None,
                "message": f"SyntaxError at line {e.lineno}: {e.msg}"
            }
        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            
            return {
                "valid": False,
                "error": str(e),
                "message": f"Validation failed: {str(e)}"
            }
    
    # ==================== TOOL 3: Search Memory ====================
    
    def search_memory(
        self,
        error_type: str,
        code: str = "",
        k: int = 3
    ) -> Dict[str, Any]:
        """
        Search memory for similar fixes using RAG
        
        Args:
            error_type: Type of error to search for
            code: Optional code snippet for similarity search
            k: Number of results to return
            
        Returns:
            Dict with:
                - success: bool
                - results: List[Dict] (similar fixes)
                - count: int
                - message: str
                - error: str (if failed)
        """
        if not self.memory_service:
            logger.warning("Memory service not available")
            return {
                "success": False,
                "error": "Memory service not configured",
                "results": [],
                "count": 0,
                "message": "No memory service available"
            }
        
        try:
            logger.info(f"Searching memory for {error_type}, k={k}")
            
            # Use quality-filtered search if available
            if hasattr(self.memory_service, 'search_similar_with_quality'):
                results = self.memory_service.search_similar_with_quality(
                    code if code else error_type,
                    error_type,
                    k=k,
                    min_success_rate=0.6  # Only return quality examples
                )
            else:
                results = self.memory_service.search_similar(
                    code if code else error_type,
                    error_type,
                    k=k
                )
            
            message = f"Found {len(results)} similar fixes for {error_type}"
            logger.info(message)
            
            return {
                "success": True,
                "results": results,
                "count": len(results),
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Memory search error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "count": 0,
                "message": f"Memory search failed: {str(e)}"
            }
    
    # ==================== Tool Declarations for Gemini ====================
    
    def get_tool_declarations(self):
        """
        Get tool declarations for Gemini Function Calling
        
        Returns:
            List of tool declarations for Gemini
        """
        from google.generativeai.types import FunctionDeclaration, Tool
        
        # Define function declarations
        execute_code_func = FunctionDeclaration(
            name="execute_code",
            description=(
                "Execute Python code safely in an isolated environment and return results. "
                "Use this to test if code runs correctly, see actual errors, and verify fixes. "
                "Returns stdout, stderr, exit code, and execution time. "
                "Timeout: 5 seconds by default."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Optional timeout in seconds (default: 5)"
                    }
                },
                "required": ["code"]
            }
        )
        
        validate_syntax_func = FunctionDeclaration(
            name="validate_syntax",
            description=(
                "Validate Python code syntax without executing it. "
                "Use this to check for syntax errors before attempting execution. "
                "Returns validation status, error details including line number and message if invalid."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to validate"
                    }
                },
                "required": ["code"]
            }
        )
        
        search_memory_func = FunctionDeclaration(
            name="search_memory",
            description=(
                "Search the knowledge base for similar code fixes and solutions. "
                "Use this to find proven solutions for similar errors from past fixes, "
                "Stack Overflow, documentation, and Reddit. "
                "Returns up to k similar fixes with their code and solutions."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "error_type": {
                        "type": "string",
                        "description": "Type of error (e.g., 'IndexError', 'TypeError', 'KeyError')"
                    },
                    "code": {
                        "type": "string",
                        "description": "Optional code snippet for similarity matching"
                    },
                    "k": {
                        "type": "integer",
                        "description": "Number of results to return (default: 3)"
                    }
                },
                "required": ["error_type"]
            }
        )
        
        # Return as Tool object
        return Tool(function_declarations=[
            execute_code_func,
            validate_syntax_func,
            search_memory_func
        ])
    
    # ==================== Tool Execution ====================
    
    def execute_tool(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name with given arguments
        
        Args:
            function_name: Name of tool to execute
            arguments: Dictionary of arguments
            
        Returns:
            Tool execution results
        """
        logger.info(f"Executing tool: {function_name}")
        
        if function_name == "execute_code":
            # NEW: Use debugger for enhanced execution
            result = self.debugger.execute_with_trace(
                arguments['code'],
                arguments.get('timeout', 5)
            )
            return self._format_debug_result(result)
        
        elif function_name == "validate_syntax":
            return self.validate_syntax(**arguments)
        
        elif function_name == "search_memory":
            return self.search_memory(**arguments)
        
        else:
            return {
                "success": False,
                "error": f"Unknown tool: {function_name}"
            }

        
        # ==================== Debugging ==================== 

    def _format_debug_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format debugger result for AI consumption"""
        formatted = {
            'success': result['success'],
            'stdout': result['stdout'],
            'stderr': result['stderr']
        }
        
        if not result['success']:
            formatted.update({
                'error_type': result['error_type'],
                'error_message': result['error_message'],
                'error_line': result['error_line'],
                'variable_state': result['variables_at_error'],
                'execution_context': result['execution_context']
            })
        
        return formatted
    
