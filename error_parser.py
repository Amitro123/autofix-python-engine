#!/usr/bin/env python3
"""
Error Parser - Parse Python errors into structured form

Extracts error information from Python exceptions and traceback messages
to enable automated fixing.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from autofix.rollback import FixTransaction
from autofix.constants import ErrorType

from autofix.logging_utils import get_logger

@dataclass
class ParsedError:
    """Structured representation of a Python error"""
    error_type: str
    error_message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    missing_module: Optional[str] = None
    missing_attribute: Optional[str] = None
    missing_function: Optional[str] = None
    syntax_details: Optional[Dict[str, Any]] = None
    suggested_fix: Optional[str] = None
    confidence: Optional[float] = None
    context_lines: Optional[List[str]] = None



class ErrorParser:
    """Parse Python errors into structured format for automated fixing"""
    
    def __init__(self):
        self.python_version = sys.version_info
        self.logger = get_logger("error_parser")
        self.error_cache = {}
    
    def parse_error(self, error_output: str) -> ParsedError:
        """Parse error output string into structured error information"""
        # Extract error type and message from stderr
        lines = error_output.strip().split('\n')
        error_line = None
        
        # Find the actual error line (usually the last line)
        for line in reversed(lines):
            if ':' in line and any(err_type in line for err_type in [
                'Error', 'Exception', 'Warning'
            ]):
                error_line = line
                break
        
        if not error_line:
            return ParsedError(
                error_type=ErrorType.UNKNOWN_ERROR.to_string(),
                error_message=error_output
            )
        
        # Parse error type and message
        if ':' in error_line:
            error_type, error_message = error_line.split(':', 1)
            error_type = error_type.strip()
            error_message = error_message.strip()
        else:
            error_type = "UnknownError"
            error_message = error_line
        
        # Extract file path and line number from traceback
        file_path = None
        line_number = None
        
        for line in lines:
            if 'File "' in line and 'line ' in line:
                # Extract file path
                file_match = re.search(r'File "([^"]+)"', line)
                if file_match:
                    file_path = file_match.group(1)
                
                # Extract line number
                line_match = re.search(r'line (\d+)', line)
                if line_match:
                    line_number = int(line_match.group(1))
        
        # Handle specific error types
        missing_module = None
        if error_type == "ModuleNotFoundError":
            module_match = re.search(r"No module named ['\"]([^'\"]+)['\"]", error_message)
            if module_match:
                missing_module = module_match.group(1)
        
        return ParsedError(
            error_type=error_type,
            error_message=error_message,
            file_path=file_path,
            line_number=line_number,
            missing_module=missing_module
        )

    def parse_exception(self, exception: Exception, script_path: str) -> ParsedError:
        """Parse an exception object into structured error information with caching"""
        # Create cache key including script path for context-aware caching
        cache_key = (type(exception).__name__, str(exception), script_path)
        
        if cache_key in self.error_cache:
            return self.error_cache[cache_key]

        parsed = self._parse_exception_impl(exception, script_path)
        self.error_cache[cache_key] = parsed
        return parsed
    
    def _parse_exception_impl(self, exception: Exception, script_path: str) -> ParsedError:
        """Internal implementation of exception parsing"""
        error_type = type(exception).__name__
        error_message = str(exception)

        line_number = self._extract_line_number(exception)
        context = self._extract_context(script_path, line_number)
        
        if isinstance(exception, ModuleNotFoundError):
            return self._parse_module_not_found(exception, script_path, line_number, context)
        elif isinstance(exception, ImportError):
            return self._parse_import_error(exception, script_path)
        elif isinstance(exception, NameError):
            return self._parse_name_error(exception, script_path)
        elif isinstance(exception, AttributeError):
            return self._parse_attribute_error(exception, script_path)
        elif isinstance(exception, SyntaxError):
            return self._parse_syntax_error(exception, script_path)
        elif isinstance(exception, IndexError):
            return self._parse_index_error(exception, script_path)
        else:
            return ParsedError(
                error_type=error_type,
                error_message=error_message,
                file_path=script_path,
                line_number=line_number,
                context_lines=context
            )
    
    def clear_cache(self):
        """Clear error cache when script files are modified"""
        self.error_cache.clear()
    
    def _extract_line_number(self, exception: Exception) -> Optional[int]:
        """Extract line number from exception traceback"""
        import traceback
        if hasattr(exception, '__traceback__') and exception.__traceback__:
            tb = exception.__traceback__
            while tb.tb_next: 
                tb = tb.tb_next
            return tb.tb_lineno
        return None

    def _extract_context(self, script_path: str, line_number: Optional[int]) -> Optional[List[str]]:
        """Extract context lines around the error"""
        if not line_number:
            return None
        try:
            lines = Path(script_path).read_text(encoding='utf-8').splitlines()
            start = max(0, line_number - 2)
            end = min(len(lines), line_number + 1)
            return lines[start:end]
        except (FileNotFoundError, PermissionError) as e:
            self.logger.warning(f"Cannot read file {script_path}: {e}")
            return None
        except UnicodeDecodeError as e:
            self.logger.warning(f"Encoding error reading {script_path}: {e}")
            return None
        except OSError as e:
            self.logger.warning(f"OS error reading {script_path}: {e}")
            return None   

    
    def _parse_module_not_found(self, exception: ModuleNotFoundError, script_path: str, line_number: Optional[int], context: Optional[List[str]]) -> ParsedError:
        """Parse ModuleNotFoundError"""
        missing_module = exception.name
        suggested_fix = f"pip install {missing_module}"

        return ParsedError(
            error_type=ErrorType.MODULE_NOT_FOUND.to_string(),
            error_message=str(exception),
            file_path=script_path,
            line_number=line_number,
            missing_module=missing_module,
            suggested_fix=suggested_fix,
            confidence=0.8,
            context_lines=context
        )
    
    def _parse_import_error(self, exception: ImportError, script_path: str) -> ParsedError:
        """Parse ImportError"""
        error_message = str(exception)
        fixes: List[Dict[str, Any]] = []
        
        # Extract module name from various ImportError patterns
        missing_module = None
        
        # Pattern: "cannot import name 'X' from 'Y'"
        import_match = re.search(r"cannot import name '([^']+)' from '([^']+)'", error_message)
        if import_match:
            missing_function = import_match.group(1)
            missing_module = import_match.group(2)
            return ParsedError(
                error_type="ImportError",
                error_message=error_message,
                file_path=script_path,
                missing_module=missing_module,
                missing_function=missing_function
            )
        
        # Pattern: "No module named 'X'"
        module_match = re.search(r"No module named '([^']+)'", error_message)
        if module_match:
            missing_module = module_match.group(1)
        
        return ParsedError(
            error_type="ImportError",
            error_message=error_message,
            file_path=script_path,
            missing_module=missing_module
        )
    
    def _parse_name_error(self, exception: NameError, script_path: str) -> ParsedError:
        """Parse NameError"""
        error_message = str(exception)
        
        # Pattern: "name 'X' is not defined"
        name_match = re.search(r"name '([^']+)' is not defined", error_message)
        missing_function = name_match.group(1) if name_match else None
        
        return ParsedError(
            error_type="NameError",
            error_message=error_message,
            file_path=script_path,
            missing_function=missing_function
        )
    

    
    def _parse_attribute_error(self, exception: AttributeError, script_path: str) -> ParsedError:
        """Parse AttributeError"""
        error_message = str(exception)
        
        # Pattern: "'X' object has no attribute 'Y'"
        attr_match = re.search(r"'([^']+)' object has no attribute '([^']+)'", error_message)
        if attr_match:
            object_name = attr_match.group(1)
            missing_attribute = attr_match.group(2)
            return ParsedError(
                error_type="AttributeError",
                error_message=error_message,
                file_path=script_path,
                missing_module=object_name,
                missing_attribute=missing_attribute
            )
        
        return ParsedError(
            error_type="AttributeError",
            error_message=error_message,
            file_path=script_path
        )
    
    def _parse_syntax_error(self, exception: SyntaxError, script_path: str) -> ParsedError:
        """Parse SyntaxError"""
        error_message = str(exception)
        
        syntax_details = {
            "text": getattr(exception, 'text', None),
            "offset": getattr(exception, 'offset', None),
            "end_offset": getattr(exception, 'end_offset', None),
        }
        
        # Check for version-specific syntax issues
        version_issue = self._detect_version_syntax_issue(error_message)
        if version_issue:
            syntax_details["version_issue"] = version_issue
        
        return ParsedError(
            error_type="SyntaxError",
            error_message=error_message,
            file_path=script_path,
            line_number=getattr(exception, 'lineno', None),
            syntax_details=syntax_details
        )
    
    def _detect_version_syntax_issue(self, error_message: str) -> Optional[Dict[str, Any]]:
        """Detect Python version-specific syntax issues"""
        current_version = self.python_version
        
        # Handle both sys.version_info objects and tuples for testing
        if hasattr(current_version, 'major'):
            version_str = f"{current_version.major}.{current_version.minor}"
        else:
            version_str = f"{current_version[0]}.{current_version[1]}"
        
        # f-string syntax (Python 3.6+)
        if "invalid syntax" in error_message.lower() and ("f'" in error_message or 'f"' in error_message):
            if current_version < (3, 6):
                return {
                    "feature": "f-strings",
                    "required_version": "3.6+",
                    "current_version": version_str,
                    "suggestion": "Use .format() or % formatting instead"
                }
        
        # Walrus operator (Python 3.8+)
        if ":=" in error_message:
            if current_version < (3, 8):
                return {
                    "feature": "walrus operator (:=)",
                    "required_version": "3.8+",
                    "current_version": version_str,
                    "suggestion": "Refactor without walrus operator"
                }
        
        # Match statement (Python 3.10+)
        if "match" in error_message.lower() and "case" in error_message.lower():
            if current_version < (3, 10):
                return {
                    "feature": "match statements",
                    "required_version": "3.10+",
                    "current_version": version_str,
                    "suggestion": "Use if/elif statements instead"
                }
        
        # Positional-only parameters (Python 3.8+)
        if "/" in error_message and "positional" in error_message.lower():
            if current_version < (3, 8):
                return {
                    "feature": "positional-only parameters",
                    "required_version": "3.8+",
                    "current_version": version_str,
                    "suggestion": "Remove '/' from function signature"
                }
        
        return None
    
    def _parse_index_error(self, exception: IndexError, script_path: str) -> ParsedError:
        """Parse IndexError"""
        error_message = str(exception)
        line_number = self._extract_line_number(exception)
        context = self._extract_context(script_path, line_number)
        
        # Extract information about the index error
        suggested_fix = "Add bounds checking before accessing list/string indices"
        
        # Try to extract more specific information from the error message
        if "list index out of range" in error_message:
            suggested_fix = "Check list length before accessing: if len(my_list) > index:"
        elif "string index out of range" in error_message:
            suggested_fix = "Check string length before accessing: if len(my_string) > index:"
        
        return ParsedError(
            error_type="IndexError",
            error_message=error_message,
            file_path=script_path,
            line_number=line_number,
            suggested_fix=suggested_fix,
            confidence=0.7,
            context_lines=context
        )
    
    def apply_fix_with_transaction(self, script_path: str, fix_function, *args, **kwargs) -> bool:
        """
        Apply a fix function with transaction support and automatic rollback.
        
        Args:
            script_path: Path to the script file
            fix_function: Function that applies the fix
            *args, **kwargs: Arguments to pass to the fix function
            
        Returns:
            bool: True if fix was successful, False otherwise
        """
        script_file = Path(script_path)
        
        try:
            with FixTransaction(script_file) as transaction:
                self.logger.info(f"Starting transactional fix for {script_path}")
                
                # Apply the fix function
                result = fix_function(script_path, *args, **kwargs)
                
                if not result:
                    raise ValueError("Fix function returned False - fix failed")
                
                self.logger.success(f"Fix applied successfully to {script_path}")
                return True
                
        except ValueError as e:
            self.logger.error(f"Fix validation failed for {script_path}: {e}")
            self.logger.info("File has been automatically restored from backup")
            return False
        except (FileNotFoundError, PermissionError) as e:
            self.logger.error(f"File access error for {script_path}: {e}")
            self.logger.info("File has been automatically restored from backup")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during fix for {script_path}: {e}")
            self.logger.info("File has been automatically restored from backup")
            return False
    
    def create_safe_fix_context(self, script_path: str):
        """
        Create a context manager for safe file fixing with automatic rollback.
        
        Usage:
            with parser.create_safe_fix_context("script.py") as ctx:
                # Apply fixes here
                ctx.apply_fix(some_fix_function, arg1, arg2)
        """
        return SafeFixContext(script_path, self.logger)


class SafeFixContext:
    """Context manager for safe file fixing with transaction support"""
    
    def __init__(self, script_path: str, logger):
        self.script_path = script_path
        self.script_file = Path(script_path)
        self.logger = logger
        self.transaction = None
        self.fixes_applied = []
    
    def __enter__(self):
        """Enter the safe fix context"""
        self.transaction = FixTransaction(self.script_file)
        self.transaction.__enter__()
        self.logger.info(f"Started safe fix context for {self.script_path}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the safe fix context"""
        if exc_type:
            self.logger.error(f"Error in safe fix context: {exc_val}")
            self.logger.info("All changes will be rolled back automatically")
        else:
            self.logger.success(f"Safe fix context completed successfully for {self.script_path}")
            if self.fixes_applied:
                self.logger.info(f"Applied {len(self.fixes_applied)} fixes: {', '.join(self.fixes_applied)}")
        
        return self.transaction.__exit__(exc_type, exc_val, exc_tb)
    
    def apply_fix(self, fix_function, *args, **kwargs):
        """Apply a fix function within the safe context"""
        fix_name = getattr(fix_function, '__name__', 'unknown_fix')
        
        try:
            self.logger.attempt(f"Applying fix: {fix_name}")
            result = fix_function(self.script_path, *args, **kwargs)
            
            if result:
                self.fixes_applied.append(fix_name)
                self.logger.success(f"Fix applied successfully: {fix_name}")
                return True
            else:
                raise ValueError(f"Fix function {fix_name} returned False")
                
        except ValueError as e:
            self.logger.error(f"Fix validation failed for {fix_name}: {e}")
            raise  # Re-raise to trigger rollback
        except (FileNotFoundError, PermissionError) as e:
            self.logger.error(f"File access error in fix {fix_name}: {e}")
            raise  # Re-raise to trigger rollback
        except Exception as e:
            self.logger.error(f"Unexpected error in fix {fix_name}: {e}")
            raise  # Re-raise to trigger rollback