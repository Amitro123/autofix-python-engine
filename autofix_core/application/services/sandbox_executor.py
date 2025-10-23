"""
Secure Sandbox Executor
Multi-layer isolation for safe code execution

PLATFORM NOTES:
- Linux/Unix: Full resource limits (CPU, memory) via resource module
- Windows: Timeout-only restrictions (resource module not available)
  Windows users should be aware that memory/CPU limits are not enforced
"""

import subprocess
import tempfile
import os
import sys
from typing import Dict, Any
from autofix_core.shared.helpers.logging_utils import get_logger

logger = get_logger(__name__)


class SandboxExecutor:
    """
    Secure sandboxed code execution with multiple security layers
    
    Security Features:
    1. Subprocess isolation
    2. Blocked dangerous imports (os, subprocess, socket, etc.)
    3. Disabled dangerous builtins (open, eval, exec)
    4. Resource limits (Linux/Unix only - CPU time, memory)
    5. Restricted environment variables
    6. Temp directory execution only
    7. No stdin access (prevents infinite input() waits)
    
    Platform Support:
    - Linux/Unix: Full security features including resource limits
    - Windows: All features except resource limits (timeout only)
    """
    
    def __init__(self):
        self.timeout = 5  # seconds
        self.max_output_size = 10000  # characters
        self.max_memory = 128 * 1024 * 1024  # 128 MB (Linux only)
        self.max_cpu_time = 5  # 5 seconds (Linux only)
    
    def execute_code(self, code: str, timeout: int = None) -> Dict[str, Any]:
        """
        Execute Python code in secure sandbox
        
        Args:
            code: Python code to execute
            timeout: Max execution time in seconds (default: 5)
            
        Returns:
            Dict with success, stdout, stderr, exit_code
        """
        timeout = timeout or self.timeout
        
        # Wrap code in sandbox restrictions
        sandbox_code = self._wrap_in_sandbox(code)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(sandbox_code)
            temp_file = f.name
        
        try:
            logger.info(f"Executing code in sandbox (timeout: {timeout}s)")
            
            # Execute in subprocess with restrictions
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,  # ← NEW: Prevent input() blocks
                cwd=tempfile.gettempdir(),  # Run in temp directory
                env=self._get_restricted_env()  # Restricted environment
            )
            
            # Truncate output if too large
            stdout = result.stdout[:self.max_output_size]
            stderr = result.stderr[:self.max_output_size]
            
            success = result.returncode == 0
            
            if success:
                logger.info("Sandbox execution successful")
            else:
                logger.warning(f"Sandbox execution failed with exit code {result.returncode}")
            
            return {
                'success': success,
                'stdout': stdout,
                'stderr': stderr,
                'exit_code': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            logger.warning(f"Sandbox execution timeout after {timeout}s")
            return {
                'success': False,
                'error': f'Execution timeout ({timeout}s)',
                'stdout': '',
                'stderr': f'TimeoutError: Code execution exceeded {timeout} second limit',
                'exit_code': -1
            }
        
        except Exception as e:
            logger.error(f"Sandbox execution error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'stdout': '',
                'stderr': f'ExecutionError: {str(e)}',
                'exit_code': -1
            }
        
        finally:
            # Always cleanup temp file
            try:
                os.unlink(temp_file)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_file}: {e}")
    
    def _wrap_in_sandbox(self, code: str) -> str:
        """
        Wrap user code in security restrictions
        """
        import textwrap
        # Remove leading indentation from code
        clean_code = textwrap.dedent(code)
        
        return f'''import sys
import builtins

# ==============================================================================
# SECURITY LAYER 1: Resource Limits (Linux/Unix only)
# ==============================================================================
try:
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, ({self.max_cpu_time}, {self.max_cpu_time}))
    resource.setrlimit(resource.RLIMIT_AS, ({self.max_memory}, {self.max_memory}))
except (ImportError, AttributeError):
    # Windows doesn't support resource module
    # Relying on subprocess timeout for execution limits
    pass

# ==============================================================================
# SECURITY LAYER 2: Blocked Dangerous Modules
# ==============================================================================
BLOCKED_MODULES = {{
    # File system access
    'os', 'pathlib', 'shutil', 'glob', 'tempfile',
    # Process/system control
    'subprocess', 'multiprocessing', 'threading', 'asyncio',
    # Network access
    'socket', 'urllib', 'urllib3', 'requests', 'http', 'ftplib', 'smtplib',
    'webbrowser',  # ← NEW: Can open external browsers
    # Code execution
    'importlib', 'runpy', 'code', 'codeop',
    # Serialization (can execute code)
    'pickle', 'shelve', 'marshal', 'dill',  # ← NEW: dill is pickle alternative
    # Database access
    'sqlite3', 'dbm',
    # Low-level access
    'ctypes', 'cffi', 'mmap',
    # I/O and logging (can write files)
    'logging',  # ← NEW: Can write to files via handlers
    # Other dangerous
    'pty', 'tty', 'termios', 'fcntl', 'ioctl',
    # XML/HTML (XXE vulnerabilities)
    'xml',  # ← NEW: XML external entity attacks
}}

# Override __import__ to block dangerous imports
_original_import = builtins.__import__

def _safe_import(name, *args, **kwargs):
    """Only allow safe imports"""
    module_root = name.split('.')[0]
    if module_root in BLOCKED_MODULES:
        raise ImportError(
            f"Import of '{{name}}' is blocked for security reasons. "
            f"Sandbox only allows safe modules like: math, json, re, time, etc."
        )
    return _original_import(name, *args, **kwargs)

builtins.__import__ = _safe_import

# ==============================================================================
# SECURITY LAYER 3: Disable Dangerous Builtins
# ==============================================================================

# Disable file operations
def _blocked_open(*args, **kwargs):
    raise PermissionError("File operations are not allowed in sandbox")

# Disable dynamic code execution
def _blocked_eval(*args, **kwargs):
    raise PermissionError("eval() is not allowed in sandbox")

def _blocked_exec(*args, **kwargs):
    raise PermissionError("exec() is not allowed in sandbox")

# Remove dangerous functions from user's global namespace
_user_globals = {{
    '__builtins__': {{
        k: v for k, v in builtins.__dict__.items() 
        if k not in ('exec', 'eval', 'open', '__import__')
    }}
}}
_user_globals['__builtins__']['__import__'] = _safe_import
_user_globals['__builtins__']['open'] = _blocked_open
_user_globals['__builtins__']['eval'] = _blocked_eval
_user_globals['__builtins__']['exec'] = _blocked_exec

# ==============================================================================
# EXECUTE USER CODE
# ==============================================================================
try:
    exec(compile({repr(clean_code)}, '<sandbox>', 'exec'), _user_globals)
except Exception as e:
    # Print full traceback for LLM to analyze
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
    
    def _get_restricted_env(self) -> Dict[str, str]:
        """
        Get restricted environment variables
        
        Only allow minimal safe environment variables
        """
        temp_dir = tempfile.gettempdir()
        
        return {
            # Python settings
            'PYTHONDONTWRITEBYTECODE': '1',  # Don't create .pyc files
            'PYTHONPATH': '',  # No custom Python path
            'PYTHONHOME': '',  # No custom Python home
            'PYTHONSTARTUP': '',  # No startup script
            
            # Required for subprocess
            'PATH': os.environ.get('PATH', ''),
            
            # Temp directories
            'HOME': temp_dir,
            'TEMP': temp_dir,
            'TMP': temp_dir,
            'TMPDIR': temp_dir,
            
            # System
            'SYSTEMROOT': os.environ.get('SYSTEMROOT', ''),  # Required on Windows
        }
