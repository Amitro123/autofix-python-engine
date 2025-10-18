"""
Refactored DebuggerService with Template Method Pattern.
Unified execution logic with configurable tracing modes.
"""

from autofix.core.base import CodeExecutor, ExecutionResult
from RestrictedPython import compile_restricted, safe_builtins
from RestrictedPython.PrintCollector import PrintCollector
from enum import Enum
from dataclasses import dataclass, field
import sys
import io
import time
import ctypes
import traceback
import threading
from typing import Dict, Any, Optional, List, Callable
from contextlib import redirect_stdout, redirect_stderr
from autofix.helpers.logging_utils import get_logger


class ExecutionMode(Enum):
    """Execution mode configuration."""
    SIMPLE = "simple"      # Fast, minimal tracing
    TRACED = "traced"      # Full context capture


@dataclass
class ExecutionConfig:
    """Centralized execution configuration."""
    mode: ExecutionMode = ExecutionMode.SIMPLE
    timeout: int = 5
    capture_variables: bool = True
    capture_stack: bool = False
    capture_context: bool = False


class DebuggerService(CodeExecutor):
    """
    Safe code execution with configurable tracing.
    Uses Template Method pattern for unified execution flow.
    """
    
    def __init__(self):
        """Initialize debugger service."""
        self.last_execution: Optional[Dict[str, Any]] = None
        self.logger = get_logger(__name__)
        self.logger.info("DebuggerService initialized")
    
    # ==================== Public API ====================
    
    def execute(self, code: str, timeout: int = 5) -> ExecutionResult:
        """
        Execute code safely (CodeExecutor interface).
        
        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds
            
        Returns:
            ExecutionResult with standardized output
        """
        config = ExecutionConfig(mode=ExecutionMode.SIMPLE, timeout=timeout)
        return self._execute_internal(code, config)
    
    def execute_with_trace(self, code: str, timeout: int = 5) -> Dict[str, Any]:
        """
        Execute code with detailed context capture.
        Backward-compatible legacy method.
        
        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds
            
        Returns:
            Dict with detailed execution information
        """
        config = ExecutionConfig(
            mode=ExecutionMode.TRACED,
            timeout=timeout,
            capture_variables=True,
            capture_stack=True,
            capture_context=True
        )
        result = self._execute_internal(code, config)
        legacy_dict = self._to_trace_dict(result, code)
        self.last_execution = legacy_dict
        return legacy_dict
    
    def get_last_execution(self) -> Optional[Dict[str, Any]]:
        """Get the last traced execution result."""
        return self.last_execution
    
    def clear_last_execution(self) -> None:
        """Clear last execution cache."""
        self.last_execution = None
    
    # ==================== Core Execution (Template Method) ====================
    
    def _execute_internal(self, code: str, config: ExecutionConfig) -> ExecutionResult:
        """
        Template Method: Unified execution pipeline.
        All execution flows through this method.
        """
        start_time = time.time()
        mode_name = config.mode.value
        self.logger.info(f"Executing code (mode={mode_name}, timeout={config.timeout}s)")
        
        # Step 1: Validate syntax
        validation = self.validate_syntax(code)
        if not validation['valid']:
            return self._create_result(
                success=False,
                error=validation['error'],
                error_type='SyntaxError',
                start_time=start_time
            )
        
        # Step 2: Compile with RestrictedPython
        compiled_code = self._compile_code(code)
        if not compiled_code['success']:
            return self._create_result(
                success=False,
                error=compiled_code['error'],
                error_type='CompilationError',
                start_time=start_time
            )
        
        # Step 3: Setup execution environment
        globals_dict = self._get_safe_globals()
        locals_dict = {}
        output_capture = io.StringIO()
        
        # Step 4: Execute with appropriate strategy
        if config.mode == ExecutionMode.TRACED:
            result = self._execute_traced(
                compiled_code['code'],
                globals_dict,
                locals_dict,
                output_capture,
                config,
                code  # Pass original code for context
            )
        else:
            result = self._execute_simple(
                compiled_code['code'],
                globals_dict,
                locals_dict,
                output_capture,
                config
            )
        
        result.execution_time = time.time() - start_time
        return result
    
    # ==================== Execution Strategies ====================
    
    def _execute_simple(
        self,
        code: Any,
        globals_dict: Dict[str, Any],
        locals_dict: Dict[str, Any],
        output_capture: io.StringIO,
        config: ExecutionConfig
    ) -> ExecutionResult:
        """Simple execution without detailed tracing (faster)."""
        result_data = {'success': False, 'error': None, 'error_type': None}
        thread_id = None
        
        def run_code():
            nonlocal thread_id
            thread_id = threading.get_ident()
            try:
                with redirect_stdout(output_capture):
                    exec(code, globals_dict, locals_dict)
                result_data['success'] = True
            except Exception as e:
                result_data['error'] = str(e)
                result_data['error_type'] = type(e).__name__
        
        # Execute with timeout
        thread = threading.Thread(target=run_code, daemon=True)
        thread.start()
        thread.join(timeout=config.timeout)
        
        # Handle timeout
        if thread.is_alive():
            return self._handle_timeout(thread, thread_id, output_capture, config.timeout)
        
        # Extract output
        output = self._extract_output(output_capture, locals_dict)
        
        # Build result
        if result_data['success']:
            self.logger.info("✅ Code executed successfully")
            return ExecutionResult(
                success=True,
                output=output,
                variables=self._serialize_simple_variables(locals_dict)
            )
        else:
            self.logger.warning(f"❌ {result_data['error_type']}: {result_data['error']}")
            return ExecutionResult(
                success=False,
                error=result_data['error'],
                error_type=result_data['error_type'] or 'RuntimeError',
                output=output
            )
    
    def _execute_traced(
        self,
        code: Any,
        globals_dict: Dict[str, Any],
        locals_dict: Dict[str, Any],
        output_capture: io.StringIO,
        config: ExecutionConfig,
        original_code: str
    ) -> ExecutionResult:
        """Traced execution with full context capture."""
        stderr_capture = io.StringIO()
        trace_data = {
            'success': False,
            'variables': {},
            'stack_trace': [],
            'context': {}
        }
        
        try:
            with redirect_stdout(output_capture), redirect_stderr(stderr_capture):
                exec(code, globals_dict, locals_dict)
            
            # Success case
            trace_data['success'] = True
            trace_data['variables'] = self._serialize_variables(locals_dict)
            self.logger.info("✅ Code executed successfully (traced)")
            
            return ExecutionResult(
                success=True,
                output=self._extract_output(output_capture, locals_dict),
                variables=trace_data['variables']
            )
            
        except Exception as e:
            # Capture detailed error information
            exc_type, exc_value, exc_tb = sys.exc_info()
            
            trace_data['error_type'] = exc_type.__name__
            trace_data['error_message'] = str(exc_value)
            
            # Capture stack and context if enabled
            if config.capture_stack and exc_tb:
                trace_data['stack_trace'] = self._build_stack_trace(exc_tb, original_code)
                trace_data['error_line'] = self._get_error_line(exc_tb)
                trace_data['variables'] = self._capture_frame_variables(
                    self._get_error_frame(exc_tb)
                )
            
            if config.capture_context and exc_tb:
                trace_data['context'] = self._build_execution_context(
                    original_code,
                    trace_data.get('error_line'),
                    trace_data['variables']
                )
            
            self.logger.warning(f"❌ {trace_data['error_type']}: {trace_data['error_message']}")
            
            return ExecutionResult(
                success=False,
                error=str(exc_value),
                error_type=exc_type.__name__,
                output=self._extract_output(output_capture, locals_dict),
                variables=trace_data['variables']
            )
    
    # ==================== Helper Methods ====================
    
    def _compile_code(self, code: str) -> Dict[str, Any]:
        """Compile code with RestrictedPython."""
        try:
            compiled = compile_restricted(code, filename='<user_code>', mode='exec')
            
            if compiled.errors:
                return {
                    'success': False,
                    'error': '; '.join(compiled.errors)
                }
            
            return {'success': True, 'code': compiled.code}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _get_safe_globals(self) -> Dict[str, Any]:
        """Get safe globals for RestrictedPython execution."""
        return {
            '__builtins__': {
                **safe_builtins,
                '_print_': PrintCollector,
                '_getattr_': getattr,
                '_write_': lambda x: x,
                '_getiter_': lambda x: iter(x),
                '_getitem_': lambda obj, index: obj[index],
            },
            '__name__': '__main__',
            '__doc__': None,
        }
    
    def _handle_timeout(
        self,
        thread: threading.Thread,
        thread_id: Optional[int],
        output_capture: io.StringIO,
        timeout: int
    ) -> ExecutionResult:
        """Handle timeout with forced thread termination."""
        self.logger.warning(f"⏱️ Execution timeout after {timeout}s - forcing termination")
        
        # Attempt forced termination
        if thread_id:
            try:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(
                    ctypes.c_long(thread_id),
                    ctypes.py_object(SystemExit)
                )
                thread.join(timeout=0.5)  # Grace period
            except Exception as e:
                self.logger.error(f"Failed to terminate thread: {e}")
        
        # Check if still alive
        if thread.is_alive():
            self.logger.critical(
                f"🚨 SECURITY: Thread survived termination! Thread ID: {thread_id}"
            )
        
        return ExecutionResult(
            success=False,
            error=f'Execution timeout after {timeout} seconds',
            error_type='TimeoutError',
            output=output_capture.getvalue(),
            timeout=True
        )
    
    def _extract_output(self, output_capture: io.StringIO, locals_dict: Dict) -> str:
        """Extract output from capture or PrintCollector."""
        output = output_capture.getvalue()
        if 'printed' in locals_dict:
            output = locals_dict['printed']
        return output
    
    def _create_result(
        self,
        success: bool,
        error: Optional[str] = None,
        error_type: Optional[str] = None,
        start_time: Optional[float] = None
    ) -> ExecutionResult:
        """Create ExecutionResult with timing."""
        result = ExecutionResult(
            success=success,
            error=error,
            error_type=error_type
        )
        if start_time:
            result.execution_time = time.time() - start_time
        return result
    
    # ==================== Variable Serialization ====================
    
    def _serialize_simple_variables(self, variables: Dict) -> Dict[str, str]:
        """Simple variable serialization (string representation)."""
        return {
            k: str(v) 
            for k, v in variables.items() 
            if not k.startswith('_')
        }
    
    def _serialize_variables(self, variables: Dict) -> Dict[str, Any]:
        """Full variable serialization with type information."""
        return {
            name: self._serialize_value(value)
            for name, value in variables.items()
            if not name.startswith('__')
        }
    
    def _serialize_value(self, value: Any) -> Dict[str, Any]:
        """Serialize a single value with metadata."""
        result = {
            'type': type(value).__name__,
            'value': None,
            'repr': repr(value)[:200],
            'metadata': {}
        }
        
        try:
            if isinstance(value, (int, float, str, bool, type(None))):
                result['value'] = value
                
            elif isinstance(value, (list, tuple)):
                result['value'] = [self._serialize_value(item)['repr'] for item in value[:5]]
                result['metadata'] = {
                    'length': len(value),
                    'truncated': len(value) > 5
                }
                
            elif isinstance(value, dict):
                result['value'] = {
                    k: self._serialize_value(v)['repr'] 
                    for k, v in list(value.items())[:5]
                }
                result['metadata'] = {
                    'length': len(value),
                    'truncated': len(value) > 5
                }
                
            elif isinstance(value, set):
                result['value'] = [self._serialize_value(item)['repr'] for item in list(value)[:5]]
                result['metadata'] = {'length': len(value)}
                
            else:
                result['value'] = str(value)[:100]
                result['metadata']['attributes'] = [
                    attr for attr in dir(value) 
                    if not attr.startswith('_')
                ][:10]
        
        except Exception as e:
            result['value'] = f"<Error serializing: {e}>"
        
        return result
    
    def _capture_frame_variables(self, frame) -> Dict[str, Any]:
        """Capture all variables in a stack frame."""
        return {
            var_name: self._serialize_value(var_value)
            for var_name, var_value in frame.f_locals.items()
            if not (var_name.startswith('__') and var_name.endswith('__'))
        }
    
    # ==================== Stack Trace & Context ====================
    
    def _get_error_frame(self, tb):
        """Get the frame where the error occurred (last frame)."""
        while tb.tb_next:
            tb = tb.tb_next
        return tb.tb_frame
    
    def _get_error_line(self, tb) -> int:
        """Get the line number where the error occurred."""
        while tb.tb_next:
            tb = tb.tb_next
        return tb.tb_lineno
    
    def _build_stack_trace(self, tb, code: str) -> List[Dict[str, Any]]:
        """Build enhanced stack trace with code context."""
        stack = []
        code_lines = code.split('\n')
        
        while tb:
            frame = tb.tb_frame
            line_no = tb.tb_lineno
            
            # Get surrounding lines (±3)
            start = max(0, line_no - 4)
            end = min(len(code_lines), line_no + 3)
            
            context_lines = [
                {
                    'line_number': i + 1,
                    'code': code_lines[i] if i < len(code_lines) else '',
                    'is_error': (i + 1 == line_no)
                }
                for i in range(start, end)
            ]
            
            stack.append({
                'line': line_no,
                'function': frame.f_code.co_name,
                'code_context': context_lines,
                'variables': self._capture_frame_variables(frame)
            })
            
            tb = tb.tb_next
        
        return stack
    
    def _build_execution_context(
        self,
        code: str,
        error_line: Optional[int],
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build human-readable execution context for AI analysis."""
        if not error_line:
            return {}
        
        code_lines = code.split('\n')
        if error_line > len(code_lines):
            return {}
        
        error_code = code_lines[error_line - 1].strip()
        
        context = {
            'error_line_number': error_line,
            'error_line_code': error_code,
            'variables_in_scope': len(variables),
            'analysis': self._analyze_error_context(error_code, variables)
        }
        
        return context
    
    def _analyze_error_context(
        self,
        error_code: str,
        variables: Dict[str, Any]
    ) -> List[str]:
        """Analyze error context for common patterns."""
        analysis = []
        
        # IndexError/list access analysis
        if '[' in error_code and ']' in error_code:
            for var_name, var_data in variables.items():
                if var_data['type'] in ('list', 'tuple', 'str'):
                    length = var_data.get('metadata', {}).get('length', 0)
                    analysis.append(
                        f"Variable '{var_name}' is a {var_data['type']} with length {length}"
                    )
        
        # KeyError/dict access analysis
        if '[' in error_code and ('"' in error_code or "'" in error_code):
            for var_name, var_data in variables.items():
                if var_data['type'] == 'dict':
                    length = var_data.get('metadata', {}).get('length', 0)
                    analysis.append(f"Dictionary '{var_name}' has {length} keys")
        
        # TypeError/arithmetic analysis
        if any(op in error_code for op in ['+', '-', '*', '/', '%']):
            for var_name, var_data in variables.items():
                analysis.append(f"Variable '{var_name}' has type {var_data['type']}")
        
        return analysis
    
    # ==================== Legacy Compatibility ====================
    
    def _to_trace_dict(self, result: ExecutionResult, code: str) -> Dict[str, Any]:
        """Convert ExecutionResult to legacy trace dict format."""
        trace_dict = {
            'success': result.success,
            'stdout': result.output or '',
            'stderr': '',
            'error_type': result.error_type,
            'error_message': result.error,
            'error_line': None,
            'variables_at_error': result.variables or {},
            'stack_trace': [],
            'execution_context': {}
        }
        
        # Add traced variables
        if result.success:
            trace_dict['variables_at_end'] = result.variables or {}
        
        return trace_dict
