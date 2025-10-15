"""
Debugger Service - Enhanced Code Execution with Variable Tracing
Captures program state at exception points for AI-powered debugging
"""

import sys
import io
import traceback
import linecache
from typing import Dict, Any, Optional, List
from contextlib import redirect_stdout, redirect_stderr
from autofix.helpers.logging_utils import get_logger

logger = get_logger(__name__)


class DebuggerService:
    """
    Enhanced code execution with variable state tracking
    Captures local variables, stack frames, and execution context at error points
    """
    
    def __init__(self):
        """Initialize debugger service"""
        self.last_execution = None
        logger.info("DebuggerService initialized")
    
    def execute_with_trace(
        self,
        code: str,
        timeout: int = 5
    ) -> Dict[str, Any]:
        """
        Execute code and capture detailed debugging information
        
        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds
            
        Returns:
            Detailed execution result with variable states
        """
        logger.info("Executing code with variable tracing...")
        
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
        
        # Create isolated namespace
        exec_globals = {
            '__builtins__': __builtins__,
            '__name__': '__main__'
        }
        exec_locals = {}
        
        try:
            # Execute with output capture
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, exec_globals, exec_locals)
            
            # Success case
            result['success'] = True
            result['stdout'] = stdout_capture.getvalue()
            result['variables_at_end'] = self._serialize_variables(exec_locals)
            
            logger.info("✅ Code executed successfully")
            
        except SyntaxError as e:
            result['error_type'] = 'SyntaxError'
            result['error_message'] = str(e)
            result['error_line'] = e.lineno
            result['stderr'] = stderr_capture.getvalue() or traceback.format_exc()
            
            logger.warning(f"SyntaxError at line {e.lineno}: {e}")
            
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
            
            logger.warning(f"❌ {result['error_type']}: {result['error_message']}")
        
        finally:
            result['stdout'] = stdout_capture.getvalue()
        
        self.last_execution = result
        return result
    
    def _capture_frame_variables(self, frame) -> Dict[str, Any]:
        """Capture and serialize all variables in a stack frame"""
        variables = {}
        
        # Get local variables
        for var_name, var_value in frame.f_locals.items():
            # Skip internal/private variables
            if var_name.startswith('__') and var_name.endswith('__'):
                continue
            
            variables[var_name] = self._serialize_value(var_value)
        
        return variables
    
    def _serialize_value(self, value: Any) -> Dict[str, Any]:
        """
        Serialize a Python value for debugging
        Returns type, representation, and useful metadata
        """
        result = {
            'type': type(value).__name__,
            'value': None,
            'repr': repr(value)[:200],  # Limit repr length
            'metadata': {}
        }
        
        try:
            # Handle different types
            if isinstance(value, (int, float, str, bool, type(None))):
                result['value'] = value
                
            elif isinstance(value, (list, tuple)):
                result['value'] = [self._serialize_value(item)['repr'] for item in value[:5]]
                result['metadata']['length'] = len(value)
                result['metadata']['first_5_items'] = True if len(value) > 5 else False
                
            elif isinstance(value, dict):
                result['value'] = {
                    k: self._serialize_value(v)['repr'] 
                    for k, v in list(value.items())[:5]
                }
                result['metadata']['length'] = len(value)
                result['metadata']['first_5_items'] = True if len(value) > 5 else False
                
            elif isinstance(value, set):
                result['value'] = [self._serialize_value(item)['repr'] for item in list(value)[:5]]
                result['metadata']['length'] = len(value)
                
            else:
                # Complex objects
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
            
            # Get code context (3 lines before and after)
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
        """
        Build human-readable execution context
        This helps AI understand what went wrong
        """
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
        
        # Analyze common error patterns
        analysis = []
        
        # IndexError analysis
        if '[' in error_code and ']' in error_code:
            for var_name, var_data in variables.items():
                if var_data['type'] in ('list', 'tuple', 'str'):
                    length = var_data.get('metadata', {}).get('length', 0)
                    analysis.append(
                        f"Variable '{var_name}' is a {var_data['type']} "
                        f"with length {length}"
                    )
        
        # KeyError analysis
        if '[' in error_code and '"' in error_code or "'" in error_code:
            for var_name, var_data in variables.items():
                if var_data['type'] == 'dict':
                    length = var_data.get('metadata', {}).get('length', 0)
                    analysis.append(
                        f"Dictionary '{var_name}' has {length} keys"
                    )
        
        # Type error analysis
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
