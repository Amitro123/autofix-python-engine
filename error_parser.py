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

from .logging_utils import get_logger

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


class ErrorParser:
    """Parse Python errors into structured format for automated fixing"""
    
    def __init__(self):
        self.python_version = sys.version_info
        self.logger = get_logger("error_parser")
    
    def parse_exception(self, exception: Exception, script_path: str) -> ParsedError:
        """Parse an exception object into structured error information"""
        error_type = type(exception).__name__
        error_message = str(exception)
        
        if isinstance(exception, ModuleNotFoundError):
            return self._parse_module_not_found(exception, script_path)
        elif isinstance(exception, ImportError):
            return self._parse_import_error(exception, script_path)
        elif isinstance(exception, NameError):
            return self._parse_name_error(exception, script_path)
        elif isinstance(exception, AttributeError):
            return self._parse_attribute_error(exception, script_path)
        elif isinstance(exception, SyntaxError):
            return self._parse_syntax_error(exception, script_path)
        else:
            return ParsedError(
                error_type=error_type,
                error_message=error_message,
                file_path=script_path
            )
    
    def _parse_module_not_found(self, exception: ModuleNotFoundError, script_path: str) -> ParsedError:
        """Parse ModuleNotFoundError"""
        missing_module = exception.name
        return ParsedError(
            error_type="ModuleNotFoundError",
            error_message=str(exception),
            file_path=script_path,
            missing_module=missing_module
        )
    
    def _parse_import_error(self, exception: ImportError, script_path: str) -> ParsedError:
        """Parse ImportError"""
        error_message = str(exception)
        
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