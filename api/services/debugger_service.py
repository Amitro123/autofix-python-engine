"""
Refactored DebuggerService with Jules' improvements
Complete working version with output capture fixed
"""

from autofix.core.base import CodeExecutor, ExecutionResult
from RestrictedPython import compile_restricted, safe_builtins
from RestrictedPython.PrintCollector import PrintCollector
from enum import Enum
from dataclasses import dataclass
import sys
import io
import time
import ctypes
import threading
from typing import Dict, Any, Optional, List
from contextlib import redirect_stdout, redirect_stderr
from autofix.helpers.logging_utils import get_logger


class ExecutionMode(Enum):
    """Execution mode: SIMPLE (fast) or TRACED (detailed)."""
    SIMPLE = "simple"
    TRACED = "traced"


@dataclass
class ExecutionConfig:
    """Execution configuration."""
    mode: ExecutionMode = ExecutionMode.SIMPLE
    timeout: int = 5


class DebuggerService(CodeExecutor):
    """Safe code execution with configurable tracing."""
    
    def __init__(self):
        self.last_execution: Optional[Dict[str, Any]] = None
        self.logger = get_logger(__name__)
        self.logger.info("DebuggerService initialized")
    
    # ==================== Public API ====================
    
    def execute(self, code: str, timeout: int = 5) -> ExecutionResult:
        """Execute code safely (simple mode)."""
        config = ExecutionConfig(mode=ExecutionMode.SIMPLE, timeout=timeout)
        return self._execute_internal(code, config)
    
    def execute_with_trace(self, code: str, timeout: int = 5) -> Dict[str, Any]:
        """Execute with detailed context (legacy dict format)."""
        config = ExecutionConfig(mode=ExecutionMode.TRACED, timeout=timeout)
        result = self._execute_internal(code, config)
        trace_dict = self._to_trace_dict(result, code)
        self.last_execution = trace_dict
        return trace_dict
    
    def get_last_execution(self) -> Optional[Dict[str, Any]]:
        return self.last_execution
    
    def clear_last_execution(self) -> None:
        self.last_execution = None
    
    # ==================== Core Execution ====================
    
    def _execute_internal(self, code: str, config: ExecutionConfig) -> ExecutionResult:
        """Template method: unified execution pipeline."""
        start_time = time.time()
        self.logger.info(f"Executing (mode={config.mode.value}, timeout={config.timeout}s)")
        
        # Validate syntax
        validation = self.validate_syntax(code)
        if not validation['valid']:
            return ExecutionResult(
                success=False, 
                error=validation['error'], 
                error_type='SyntaxError',
                execution_time=time.time() - start_time
            )
        
        # Compile
        compiled = self._compile_code(code)
        if not compiled['success']:
            return ExecutionResult(
                success=False,
                error=compiled['error'],
                error_type='CompilationError',
                execution_time=time.time() - start_time
            )
        
        # Setup environment
        globals_dict = self._get_safe_globals()
        locals_dict = {}
        output_capture = io.StringIO()
        
        # Execute with appropriate strategy
        if config.mode == ExecutionMode.TRACED:
            result = self._execute_traced(compiled['code'], globals_dict, locals_dict, 
                                         output_capture, config, code)
        else:
            result = self._execute_simple(compiled['code'], globals_dict, locals_dict,
                                         output_capture, config)
        
        result.execution_time = time.time() - start_time
        return result
    
    def _execute_simple(self, code, globals_dict, locals_dict, output_capture, config):
        """Simple execution - WITH VARIABLE CAPTURE ON ERROR."""
        result_data = {'success': False, 'error': None, 'error_type': None}
        thread_id = None
        output_lines = []
        
        def run_code():
            nonlocal thread_id
            thread_id = threading.get_ident()
            
            # Monkey-patch builtins.print
            import builtins
            original_print = builtins.print
            
            def captured_print(*args, **kwargs):
                """Capture print calls."""
                sep = kwargs.get('sep', ' ')
                end = kwargs.get('end', '\n')
                line = sep.join(str(arg) for arg in args) + end
                output_lines.append(line)
            
            builtins.print = captured_print
            
            try:
                exec(code, globals_dict, locals_dict)
                result_data['success'] = True
            except Exception as e:
                result_data['error'] = str(e)
                result_data['error_type'] = type(e).__name__
            finally:
                # Restore original print
                builtins.print = original_print
        
        thread = threading.Thread(target=run_code, daemon=True)
        thread.start()
        thread.join(timeout=config.timeout)
        
        if thread.is_alive():
            return self._handle_timeout(thread, thread_id, output_capture, config.timeout)
        
        output = ''.join(output_lines)
        
        # ✨ CAPTURE VARIABLES EVEN ON ERROR (simple serialization)
        captured_vars = {
            k: str(v) for k, v in locals_dict.items() 
            if not k.startswith('_') and k != 'print'
        }
        
        if result_data['success']:
            self.logger.info(f"✅ Executed, {len(output_lines)} prints, {len(output)} chars")
            return ExecutionResult(
                success=True,
                output=output,
                variables=captured_vars  # ← Capture on success
            )
        else:
            self.logger.warning(f"❌ {result_data['error_type']}: {result_data['error']}")
            return ExecutionResult(
                success=False,
                error=result_data['error'],
                error_type=result_data['error_type'] or 'RuntimeError',
                output=output,
                variables=captured_vars  # ← ALSO capture on error!
            
            )
        
    def _execute_traced(self, code, globals_dict, locals_dict, output_capture, config, original_code):
        """Traced execution - WORKS WITH PRINT!"""
        output_lines = []
        
        import builtins
        original_print = builtins.print
        
        def captured_print(*args, **kwargs):
            """Capture print calls."""
            sep = kwargs.get('sep', ' ')
            end = kwargs.get('end', '\n')
            line = sep.join(str(arg) for arg in args) + end
            output_lines.append(line)
        
        builtins.print = captured_print
        
        try:
            exec(code, globals_dict, locals_dict)
            
            output = ''.join(output_lines)
            self.logger.info(f"✅ Traced, {len(output_lines)} prints, {len(output)} chars")
            
            return ExecutionResult(
                success=True,
                output=output,
                variables=self._serialize_variables(locals_dict)
            )
            
        except Exception as e:
            error_context = self._capture_error_context(e, original_code)
            output = ''.join(output_lines)
            
            self.logger.warning(f"❌ {error_context['error_type']}: {error_context['error_message']}")
            return ExecutionResult(
                success=False,
                error=error_context['error_message'],
                error_type=error_context['error_type'],
                output=output,
                variables=error_context['variables']
            )
        finally:
            # Always restore original print
            builtins.print = original_print

    
    # ==================== Error Context Capture (Jules' Suggestion) ====================
    
    def _capture_error_context(self, exception: Exception, code: str) -> Dict[str, Any]:
        """
        Capture detailed error context from exception.
        Extracted from _execute_traced per Jules' review.
        """
        exc_type, exc_value, exc_tb = sys.exc_info()
        
        context = {
            'error_type': exc_type.__name__ if exc_type else 'UnknownError',
            'error_message': str(exc_value),
            'variables': {},
            'error_line': None
        }
        
        if exc_tb:
            error_frame = self._get_error_frame(exc_tb)
            context['variables'] = self._capture_frame_variables(error_frame)
            context['error_line'] = self._get_error_line_number(exc_tb)
            
            self.logger.debug(f"Captured error context: line {context['error_line']}, "
                            f"{len(context['variables'])} variables")
        
        return context
    
    def _get_error_line_number(self, tb) -> Optional[int]:
        """Get the line number where the error occurred."""
        while tb.tb_next:
            tb = tb.tb_next
        return tb.tb_lineno
    
    # ==================== Helpers ====================
    
    def _compile_code(self, code: str) -> Dict[str, Any]:
        """
        Compile with RestrictedPython.
        FIXED: Handles direct code object return.
        """
        try:
            compiled = compile_restricted(code, '<user_code>', 'exec')
            
            # Case 1: compile_restricted returns a code object directly (common)
            if hasattr(compiled, 'co_code'):
                self.logger.debug("Got code object directly from compile_restricted")
                return {'success': True, 'code': compiled}
            
            # Case 2: Returns CompileResult object (newer RestrictedPython)
            elif hasattr(compiled, 'code') and hasattr(compiled, 'errors'):
                if compiled.errors:
                    error_msg = '; '.join(compiled.errors)
                    self.logger.warning(f"RestrictedPython errors: {error_msg}")
                    return {'success': False, 'error': error_msg}
                
                self.logger.debug("Got CompileResult from compile_restricted")
                return {'success': True, 'code': compiled.code}
            
            # Case 3: Unexpected type
            else:
                error_msg = f"Unexpected compile_restricted result: {type(compiled)}"
                self.logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
        except SyntaxError as e:
            error_msg = f"Syntax error at line {e.lineno}: {e.msg}"
            self.logger.warning(error_msg)
            return {'success': False, 'error': error_msg}
            
        except Exception as e:
            self.logger.error(f"Compilation failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _get_safe_globals(self) -> Dict[str, Any]:
        """Safe globals for RestrictedPython with common builtins."""
        return {
            '__builtins__': {
                **safe_builtins,
                '_print_': PrintCollector,
                '_getattr_': getattr,
                '_write_': lambda x: x,
                '_getiter_': lambda x: iter(x),
                '_getitem_': lambda obj, index: obj[index],
                # Add commonly needed builtins
                'sum': sum,           
                'len': len,           
                'min': min,           
                'max': max,           
                'abs': abs,           
                'round': round,       
                'sorted': sorted,     
                'enumerate': enumerate,
                'zip': zip,           
                'range': range,       
                'list': list,         
                'dict': dict,         
                'set': set,           
                'tuple': tuple,       
                'str': str,           
                'int': int,           
                'float': float,       
                'bool': bool,         
            },
            '__name__': '__main__',
            '__doc__': None,
        }
    
    def _handle_timeout(self, thread, thread_id, output_capture, timeout):
        """Handle timeout with forced termination."""
        self.logger.warning(f"⏱️ Timeout after {timeout}s - forcing termination")
        
        if thread_id:
            try:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(
                    ctypes.c_long(thread_id), ctypes.py_object(SystemExit)
                )
                thread.join(timeout=0.5)
            except Exception as e:
                self.logger.error(f"Failed to terminate: {e}")
        
        if thread.is_alive():
            self.logger.critical(f"🚨 SECURITY: Thread survived! ID: {thread_id}")
        
        return ExecutionResult(
            success=False,
            error=f'Timeout after {timeout}s',
            error_type='TimeoutError',
            output=output_capture.getvalue(),
            timeout=True
        )
    
    def _get_error_frame(self, tb):
        """Get the frame where error occurred."""
        while tb.tb_next:
            tb = tb.tb_next
        return tb.tb_frame
    
    # ==================== Serialization ====================
    
    def _serialize_variables(self, variables: Dict) -> Dict[str, Any]:
        """Serialize variables with type info."""
        return {
            name: self._serialize_value(value)
            for name, value in variables.items()
            if not name.startswith('__')
        }
    
    def _serialize_value(self, value: Any) -> Dict[str, Any]:
        """Serialize single value."""
        result = {
            'type': type(value).__name__,
            'repr': repr(value)[:200],
            'metadata': {}
        }
        
        try:
            if isinstance(value, (int, float, str, bool, type(None))):
                result['value'] = value
            elif isinstance(value, (list, tuple)):
                result['value'] = [repr(item)[:50] for item in value[:5]]
                result['metadata'] = {'length': len(value), 'truncated': len(value) > 5}
            elif isinstance(value, dict):
                result['value'] = {k: repr(v)[:50] for k, v in list(value.items())[:5]}
                result['metadata'] = {'length': len(value), 'truncated': len(value) > 5}
            elif isinstance(value, set):
                result['value'] = [repr(item)[:50] for item in list(value)[:5]]
                result['metadata'] = {'length': len(value)}
            else:
                result['value'] = str(value)[:100]
        except Exception as e:
            result['value'] = f"<Error: {e}>"
        
        return result
    
    def _capture_frame_variables(self, frame) -> Dict[str, Any]:
        """Capture variables from stack frame."""
        return {
            var_name: self._serialize_value(var_value)
            for var_name, var_value in frame.f_locals.items()
            if not (var_name.startswith('__') and var_name.endswith('__'))
        }
    
    # ==================== Legacy Compatibility ====================
    
    def _to_trace_dict(self, result: ExecutionResult, code: str) -> Dict[str, Any]:
        """Convert to legacy trace dict format."""
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
        
        if result.success:
            trace_dict['variables_at_end'] = result.variables or {}
        
        return trace_dict
