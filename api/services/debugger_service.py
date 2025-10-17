"""
Concrete implementation of CodeExecutor using RestrictedPython.
"""

from autofix.core.base import CodeExecutor, ExecutionResult
from RestrictedPython import compile_restricted, safe_builtins, safe_globals
from RestrictedPython.PrintCollector import PrintCollector
import sys
import io
import time
import traceback
import threading
from typing import Dict, Any, Optional, List
from contextlib import redirect_stdout, redirect_stderr
from autofix.helpers.logging_utils import get_logger


class DebuggerService(CodeExecutor):
    """
    Enhanced code execution with variable state tracking.
    Captures local variables, stack frames, and execution context at error points.
    """
    
    def __init__(self):
        """Initialize debugger service"""
        self.last_execution = None
        self.logger = get_logger(__name__)
        self.logger.info("DebuggerService initialized")
    
    def execute(self, code: str, timeout: int = 5) -> ExecutionResult:
        """
        Execute code safely (implements CodeExecutor interface).
        
        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds
            
        Returns:
            ExecutionResult with standardized output
        """
        start_time = time.time()
        self.logger.info("Executing code with RestrictedPython...")
        
        # Validate syntax first
        validation = self.validate_syntax(code)
        if not validation['valid']:
            return ExecutionResult(
                success=False,
                error=validation['error'],
                error_type='SyntaxError',
                execution_time=time.time() - start_time
            )
        
        # Compile with RestrictedPython
        try:
            compiled_code = compile_restricted(
                code,
                filename='<user_code>',
                mode='exec'
            )
            
            if compiled_code.errors:
                error_msg = "; ".join(compiled_code.errors)
                return ExecutionResult(
                    success=False,
                    error=error_msg,
                    error_type='CompilationError',
                    execution_time=time.time() - start_time
                )
        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e),
                error_type='CompilationError',
                execution_time=time.time() - start_time
            )
        
        # Setup safe environment with PrintCollector
        restricted_globals = self._get_safe_globals()
        local_vars = {}
        output_capture = io.StringIO()
        
        # Execute with timeout
        result = self._execute_with_timeout(
            compiled_code.code,
            restricted_globals,
            local_vars,
            output_capture,
            timeout
        )
        
        result.execution_time = time.time() - start_time
        return result
    
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
    
    def _execute_with_timeout(
        self,
        code,
        globals_dict,
        locals_dict,
        output_capture,
        timeout: int
    ) -> ExecutionResult:
        """Execute code with timeout protection."""
        result_data = {'success': False, 'error': None, 'output': ''}
        
        def run_code():
            try:
                with redirect_stdout(output_capture):
                    exec(code, globals_dict, locals_dict)
                result_data['success'] = True
            except Exception as e:
                result_data['error'] = str(e)
                result_data['error_type'] = type(e).__name__
        
        thread = threading.Thread(target=run_code, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            self.logger.warning(f"⏱️ Execution timeout after {timeout}s")
            return ExecutionResult(
                success=False,
                error=f'Execution timeout after {timeout} seconds',
                error_type='TimeoutError',
                output=output_capture.getvalue(),
                timeout=True
            )
        
        # Extract printed output
        output = output_capture.getvalue()
        if 'printed' in locals_dict:
            output = locals_dict['printed']
        
        if result_data['success']:
            self.logger.info("✅ Code executed successfully")
            return ExecutionResult(
                success=True,
                output=output,
                variables={k: str(v) for k, v in locals_dict.items() if not k.startswith('_')}
            )
        else:
            self.logger.warning(f"❌ {result_data.get('error_type', 'Error')}: {result_data['error']}")
            return ExecutionResult(
                success=False,
                error=result_data['error'],
                error_type=result_data.get('error_type', 'RuntimeError'),
                output=output
            )
    
    def execute_with_trace(self, code: str, timeout: int = 5) -> Dict[str, Any]:
        """
        Execute code and capture detailed debugging information.
        
        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds
            
        Returns:
            Detailed execution result with variable states
        """
        self.logger.info("Executing code with variable tracing...")
        
        # Prepare execution environment
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        result = {
            'success': False,
            'stdout': '',
            'stderr': '',
            'error_type': None,
            'error_message': None,
            'error_line': None,
            'variables_at_error': {},
            'stack_trace': [],
            'execution_context': {}
        }
        
        # Use safe globals with PrintCollector
        exec_globals = self._get_safe_globals()
        exec_locals = {}
        
        try:
            # Compile the code in a restricted environment
            self.logger.info("Compiling code with RestrictedPython...")
            byte_code = compile_restricted(
                code,
                filename='<inline code>',
                mode='exec'
            )
            
            if byte_code.errors:
                result['error_type'] = 'CompilationError'
                result['error_message'] = '; '.join(byte_code.errors)
                result['stderr'] = result['error_message']
                return result
            
            # Execute with output capture
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(byte_code.code, exec_globals, exec_locals)
            
            # Success case
            result['success'] = True
            result['stdout'] = stdout_capture.getvalue()
            
            # Extract printed output if PrintCollector was used
            if 'printed' in exec_locals:
                result['stdout'] = exec_locals['printed']
            
            result['variables_at_end'] = self._serialize_variables(exec_locals)
            
            self.logger.info("✅ Code executed successfully")
            
        except SyntaxError as e:
            result['error_type'] = 'SyntaxError'
            result['error_message'] = str(e)
            result['error_line'] = e.lineno
            result['stderr'] = stderr_capture.getvalue() or traceback.format_exc()
            
            self.logger.warning(f"SyntaxError at line {e.lineno}: {e}")
            
        except Exception as e:
            # Capture detailed error information
            exc_type, exc_value, exc_tb = sys.exc_info()
            
            result['error_type'] = exc_type.__name__
            result['error_message'] = str(exc_value)
            result['stderr'] = stderr_capture.getvalue() or traceback.format_exc()
            
            # Extract error line and context
            if exc_tb:
                # Get the last frame (where error occurred)
                tb_frame = exc_tb
                while tb_frame.tb_next:
                    tb_frame = tb_frame.tb_next
                
                result['error_line'] = tb_frame.tb_lineno
                
                # Capture variable states at error
                frame = tb_frame.tb_frame
                result['variables_at_error'] = self._capture_frame_variables(frame)
                
                # Build enhanced stack trace
                result['stack_trace'] = self._build_enhanced_stack_trace(exc_tb, code)
                
                # Execution context
                result['execution_context'] = self._build_execution_context(
                    code,
                    result['error_line'],
                    result['variables_at_error']
                )
            
            self.logger.warning(f"❌ {result['error_type']}: {result['error_message']}")
        
        finally:
            result['stdout'] = stdout_capture.getvalue()
            if 'printed' in exec_locals and not result['stdout']:
                result['stdout'] = exec_locals['printed']
        
        self.last_execution = result
        return result
    
    # [Rest of the helper methods stay the same]
    def _capture_frame_variables(self, frame) -> Dict[str, Any]:
        """Capture and serialize all variables in a stack frame"""
        variables = {}
        
        for var_name, var_value in frame.f_locals.items():
            if var_name.startswith('__') and var_name.endswith('__'):
                continue
            
            variables[var_name] = self._serialize_value(var_value)
        
        return variables
    
    def _serialize_value(self, value: Any) -> Dict[str, Any]:
        """Serialize a Python value for debugging"""
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
                result['metadata']['length'] = len(value)
                result['metadata']['first_5_items'] = len(value) > 5
                
            elif isinstance(value, dict):
                result['value'] = {
                    k: self._serialize_value(v)['repr'] 
                    for k, v in list(value.items())[:5]
                }
                result['metadata']['length'] = len(value)
                result['metadata']['first_5_items'] = len(value) > 5
                
            elif isinstance(value, set):
                result['value'] = [self._serialize_value(item)['repr'] for item in list(value)[:5]]
                result['metadata']['length'] = len(value)
                
            else:
                result['value'] = str(value)[:100]
                result['metadata']['attributes'] = [
                    attr for attr in dir(value) 
                    if not attr.startswith('_')
                ][:10]
        
        except Exception as e:
            result['value'] = f"<Error serializing: {e}>"
        
        return result
    
    def _serialize_variables(self, variables: dict) -> Dict[str, Any]:
        """Serialize all variables in a dict"""
        return {
            name: self._serialize_value(value)
            for name, value in variables.items()
            if not name.startswith('__')
        }
    
    def _build_enhanced_stack_trace(self, tb, code: str) -> List[Dict[str, Any]]:
        """Build enhanced stack trace with code context"""
        stack = []
        code_lines = code.split('\n')
        
        while tb:
            frame = tb.tb_frame
            line_no = tb.tb_lineno
            
            start_line = max(0, line_no - 4)
            end_line = min(len(code_lines), line_no + 3)
            
            context_lines = []
            for i in range(start_line, end_line):
                is_error_line = (i + 1 == line_no)
                context_lines.append({
                    'line_number': i + 1,
                    'code': code_lines[i] if i < len(code_lines) else '',
                    'is_error': is_error_line
                })
            
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
        error_line: int,
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build human-readable execution context"""
        code_lines = code.split('\n')
        
        if not error_line or error_line > len(code_lines):
            return {}
        
        error_code = code_lines[error_line - 1].strip()
        
        context = {
            'error_line_number': error_line,
            'error_line_code': error_code,
            'variables_in_scope': len(variables),
            'analysis': []
        }
        
        analysis = []
        
        if '[' in error_code and ']' in error_code:
            for var_name, var_data in variables.items():
                if var_data['type'] in ('list', 'tuple', 'str'):
                    length = var_data.get('metadata', {}).get('length', 0)
                    analysis.append(
                        f"Variable '{var_name}' is a {var_data['type']} "
                        f"with length {length}"
                    )
        
        if '[' in error_code and ('"' in error_code or "'" in error_code):
            for var_name, var_data in variables.items():
                if var_data['type'] == 'dict':
                    length = var_data.get('metadata', {}).get('length', 0)
                    analysis.append(
                        f"Dictionary '{var_name}' has {length} keys"
                    )
        
        if '+' in error_code or '-' in error_code or '*' in error_code:
            for var_name, var_data in variables.items():
                analysis.append(
                    f"Variable '{var_name}' has type {var_data['type']}"
                )
        
        context['analysis'] = analysis
        
        return context
    
    def get_last_execution(self) -> Optional[Dict[str, Any]]:
        """Get the last execution result"""
        return self.last_execution
    
    def clear_last_execution(self):
        """Clear last execution cache"""
        self.last_execution = None
