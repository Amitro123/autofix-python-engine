import time
import subprocess
import sys
import os
import re
import threading
import json
import argparse
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timezone
from ..helpers.logging_utils import get_logger, quick_setup
from ..helpers.spinner import spinner
from ..core.error_parser import ErrorParser, ParsedError
from ..python_fixer import PythonFixer
try:
    from autofix.handlers.syntax_error_handler import create_syntax_error_handler, SyntaxErrorType
    from ..constants import ErrorType, MetadataKey, FixStatus, SyntaxErrorSubType, RegexPatterns, EnvironmentVariables, ErrorMessagePatterns
except ImportError:
    from autofix.handlers.syntax_error_handler import create_syntax_error_handler, SyntaxErrorType
    from autofix.constants import ErrorType, MetadataKey, FixStatus
from .cli_parser import create_parser, validate_args, validate_script_path

logger = get_logger("autofix_cli_interactive")

# Module-level constants
SYNTAX_ERROR = ErrorType.SYNTAX_ERROR
MODULE_NOT_FOUND = ErrorType.MODULE_NOT_FOUND
IMPORT_ERROR = ErrorType.IMPORT_ERROR
NAME_ERROR = ErrorType.NAME_ERROR
ATTRIBUTE_ERROR = ErrorType.ATTRIBUTE_ERROR
INDEX_ERROR = ErrorType.INDEX_ERROR
TYPE_ERROR = ErrorType.TYPE_ERROR
INDENTATION_ERROR = ErrorType.INDENTATION_ERROR
TAB_ERROR = ErrorType.TAB_ERROR


SHOW_METRICS_ERRORS = os.getenv('AUTOFIX_DEBUG_METRICS', 'false').lower() == 'true' #debug metrics WHERE TO SET IT?

# Firebase Admin SDK for production metrics (transparent to users)
METRICS_ENABLED = False
metrics_collector = None
__app_id = EnvironmentVariables.DEFAULT_APP_ID

try:
    from ..integrations import get_metrics_collector
    metrics_collector = get_metrics_collector()
    METRICS_ENABLED = metrics_collector.client is not None
    if METRICS_ENABLED:
        __app_id = metrics_collector.app_id
    else:
        __app_id = EnvironmentVariables.DEFAULT_APP_ID

except ImportError as e:
    metrics_collector = None  
    METRICS_ENABLED = False
    __app_id = EnvironmentVariables.DEFAULT_APP_ID
    logger.debug(f"Metrics disabled: {e}")


@dataclass
class ErrorDetails:
    """Structured error details"""
    error_type: str
    line_number: Optional[int] = None
    suggestion: str = "Fix the error"
    extra_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extra_data is None:
            self.extra_data = {}

class ErrorHandler(ABC):
    """Abstract base class for error handlers"""
    @abstractmethod
    def can_handle(self, error_output: str) -> bool:
        """Check if this handler can process the error"""
        pass
    
    @abstractmethod
    def extract_details(self, error_output: str) -> ErrorDetails:
        """Extract error details from output"""
        pass
    
    @abstractmethod
    def fix_error(self, script_path: str, details: ErrorDetails) -> bool:
        """Attempt to fix the error"""
        pass
    
    @property
    @abstractmethod
    def error_name(self) -> str:
        """Human-readable error name"""
        pass

class ModuleNotFoundErrorHandler(ErrorHandler):
    """CLI ErrorHandler for ModuleNotFoundError - uses the unified handler"""
    
    def __init__(self):
        # Use the unified handler instead of direct PackageInstaller
        from ..handlers.module_not_found_handler import (
            ModuleNotFoundHandler as UnifiedHandler,
            ModuleValidation
        )
        self.unified_handler = UnifiedHandler(auto_install=True, create_files=True)
        self.validation = ModuleValidation()
    
    def can_handle(self, error_output: str) -> bool:
        return MODULE_NOT_FOUND.to_string() in error_output
    
    def extract_details(self, error_output: str) -> ErrorDetails:
        match = re.search(RegexPatterns.MODULE_NAME, error_output)
        module_name = match.group(1) if match else None
        
        line_match = re.search(RegexPatterns.LINE_NUMBER, error_output)
        line_number = int(line_match.group(1)) if line_match else None
        
        suggestion = self._get_advanced_suggestion(module_name) if module_name else "Check module name and installation"
        
        return ErrorDetails(
            error_type=MODULE_NOT_FOUND.to_string(),
            line_number=line_number,
            suggestion=suggestion,
            extra_data={MetadataKey.MODULE_NAME: module_name}
        )
    
    def _get_advanced_suggestion(self, module_name: str) -> str:
        """Generate advanced suggestions using unified handler"""
        if not module_name:
            return "Check module name and installation"
        
        # Use the unified handler's analyze_error
        can_fix, suggestion, _ = self.unified_handler.analyze_error(
            f"No module named '{module_name}'",
            ""
        )
        
        return suggestion
    
    def fix_error(self, script_path: str, details: ErrorDetails) -> bool:
        """Fix error using unified handler"""
        module_name = details.extra_data.get(MetadataKey.MODULE_NAME)
        
        if not module_name:
            return False
        
        # Use the unified handler's apply_fix
        error_message = f"No module named '{module_name}'"
        _, _, error_details = self.unified_handler.analyze_error(error_message, script_path)
        
        return self.unified_handler.apply_fix(
            "ModuleNotFoundError",
            script_path,
            error_details
        )
    
    @property
    def error_name(self) -> str:
        return MODULE_NOT_FOUND.to_string()


class TypeErrorHandler(ErrorHandler):
    def can_handle(self, error_output: str) -> bool:
        return TYPE_ERROR.to_string() in error_output
    
    def extract_details(self, error_output: str) -> ErrorDetails:
        line_matches = re.findall(RegexPatterns.LINE_NUMBER, error_output)
        line_number = int(line_matches[-2] if len(line_matches) > 1 else line_matches[0]) if line_matches else None
        
        # Advanced TypeError pattern matching
        error_type, suggestion = self._analyze_type_error(error_output)
        
        return ErrorDetails(
            error_type=error_type, 
            line_number=line_number, 
            suggestion=suggestion,
            extra_data={MetadataKey.ERROR_OUTPUT.value: error_output}
        )
    
    def _analyze_type_error(self, error_output: str) -> Tuple[str, str]:
        """Advanced analysis of TypeError patterns"""
        # Unsupported operand types
        if ErrorMessagePatterns.UNSUPPORTED_OPERAND in error_output or ErrorMessagePatterns.UNSUPPORTED_OPERAND in error_output:
            return SyntaxErrorSubType.SYNTAX_UNSUPPORTED_OPERAND, "Fix type mismatch in operation (add type conversion)"
        
        # Function argument issues
        if "takes" in error_output and ErrorMessagePatterns.POSITIONAL_ARGUMENT in error_output:
            return "argument_count", "Fix function argument count mismatch"
        
        if "missing" in error_output and "required positional argument" in error_output:
            return "missing_argument", "Add missing required function arguments"
        
        # Object attribute/method issues
        if "object has no attribute" in error_output:
            return "missing_attribute", "Check object type and available attributes/methods"
        
        # Iteration issues
        if "not iterable" in error_output:
            return "not_iterable", "Object cannot be iterated - check if it's a list/tuple/dict"
        
        # Subscript issues
        if "not subscriptable" in error_output:
            return "not_subscriptable", "Object doesn't support indexing - check if it's a sequence"
        
        # Callable issues
        if "not callable" in error_output:
            return "not_callable", "Object is not a function - check if parentheses are needed"
        
        return "general_type", "Fix type-related error"
    
    def fix_error(self, script_path: str, details: ErrorDetails) -> bool:
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if not details.line_number or details.line_number > len(lines):
                return False
            
            line_idx = details.line_number - 1
            current_line = lines[line_idx]
            fixed_line = self._apply_type_fix(current_line, details)
            
            if fixed_line != current_line:
                lines[line_idx] = fixed_line
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                logger.info(f"Fixed TypeError on line {details.line_number}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to fix TypeError: {e}")
            return False
    
    def _apply_type_fix(self, line: str, details: ErrorDetails) -> str:
        """Apply specific fixes based on error type"""
        error_type = details.error_type
        
        if error_type ==  SyntaxErrorSubType.UNSUPPORTED_OPERAND.value:
            # Fix string + number concatenation
            line = re.sub(RegexPatterns.STRING_PLUS_NUMBER_1, r'\1 + str(\2)', line)
            line = re.sub(RegexPatterns.STRING_PLUS_NUMBER_2, r'str(\1) + \2', line)
            line = re.sub(RegexPatterns.STRING_PLUS_NUMBER_3, r'\1 + str(\2)', line)
            
            # Fix list + string issues
            line = re.sub(RegexPatterns.LIST_PLUS_STRING, r'\1 + [\2]', line)
        
        elif error_type == SyntaxErrorSubType.NOT_ITERABLE.value:
            # Add list conversion for common cases
            if 'for' in line and 'in' in line:
                # Convert: for x in variable -> for x in [variable] if variable is not iterable
                line = re.sub(RegexPatterns.FOR_IN_VARIABLE, r'for \1 in [\2] if isinstance(\2, (list, tuple)) else \2', line)
        
        elif error_type == SyntaxErrorSubType.NOT_SUBSCRIPTABLE.value:
            # Convert indexing to attribute access where appropriate
            line = re.sub(RegexPatterns.INDEX_ACCESS, r'getattr(\1, "item_\2", None)', line)
        
        return line
    
    @property
    def error_name(self) -> str:
        return TYPE_ERROR.to_string()

class IndentationErrorHandler(ErrorHandler):
    def can_handle(self, error_output: str) -> bool:
        return INDENTATION_ERROR.to_string() in error_output
    
    def extract_details(self, error_output: str) -> ErrorDetails:
        line_match = re.search(RegexPatterns.LINE_NUMBER, error_output)
        line_number = int(line_match.group(1)) if line_match and line_match.group(1) else None

        
        if "expected an indented block" in error_output:
            error_type = SyntaxErrorSubType.MISSING_INDENTATION.value
            suggestion = "Add proper indentation to the code block"
        elif "unindent does not match" in error_output:
            error_type = SyntaxErrorSubType.INCONSISTENT_INDENTATION.value
            suggestion = "Fix inconsistent indentation"
        elif "unexpected indent" in error_output:
            error_type = SyntaxErrorSubType.UNEXPECTED_INDENT.value
            suggestion = "Remove unnecessary indentation"
        else:
            error_type = "general_indentation"
            suggestion = "Fix indentation issues"
        
        return ErrorDetails(error_type=error_type, line_number=line_number, suggestion=suggestion)
    
    def fix_error(self, script_path: str, details: ErrorDetails) -> bool:
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if details.error_type == SyntaxErrorSubType.MISSING_INDENTATION.value and details.line_number:
                line_idx = details.line_number - 1
                if line_idx < len(lines):
                    current_line = lines[line_idx].strip()
                    if current_line:
                        # Add 4 spaces indentation
                        lines[line_idx] = '    ' + current_line + '\n'
            elif details.error_type == SyntaxErrorSubType.INCONSISTENT_INDENTATION.value:
                # Convert tabs to spaces
                lines = [line.expandtabs(4) for line in lines]
            elif details.error_type == SyntaxErrorSubType.UNEXPECTED_INDENT.value and details.line_number:
                line_idx = details.line_number - 1
                if line_idx < len(lines):
                    lines[line_idx] = lines[line_idx].lstrip() + '\n'
            
            with open(script_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            return True
        except Exception:
            return False
    
    @property
    def error_name(self) -> str:
        return INDENTATION_ERROR.to_string()

class TabErrorHandler(ErrorHandler):
    def can_handle(self, error_output: str) -> bool:
        return "TabError" in error_output or "inconsistent use of tabs and spaces" in error_output
    
    @property
    def error_name(self) -> str:
        return "TabError"
    
    def description(self) -> str:
        return "Convert tabs to spaces for consistent indentation"
    
    def extract_details(self, error_output: str) -> ErrorDetails:
        """Extract details from TabError output"""
        line_number = None
    
        # Parse line number from error message
        import re
        line_match = re.search(r'line (\d+)', error_output)
        if line_match:
            line_number = int(line_match.group(1))
    
        return ErrorDetails(
            error_type=ErrorType.TAB_ERROR.value,
            line_number=line_number,
            suggestion="Convert tabs to spaces for consistent indentation",
            extra_data={}
        )
    
    def fix_error(self, script_path: str, details: ErrorDetails) -> bool:
        """Convert tabs to spaces"""
        if not script_path:
            logger.error("fix_error called with None or empty script_path")
            return False
        
        try:
            content = Path(script_path).read_text(encoding='utf-8')
            fixed_content = content.expandtabs(4)  # Convert tabs to 4 spaces
            
            if content != fixed_content:
                # Create backup
                backup_path = f"{script_path}.backup"
                Path(backup_path).write_text(content, encoding='utf-8')
                
                # Write fixed content
                Path(script_path).write_text(fixed_content, encoding='utf-8')
                logger.info(f"Converted tabs to spaces in {script_path}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to fix TabError: {e}")
            return False

class IndexErrorHandler(ErrorHandler):#amitro to do
    def can_handle(self, error_output: str) -> bool:
        return INDEX_ERROR.to_string() in error_output
    
    def extract_details(self, error_output: str) -> ErrorDetails:
        line_match = re.search(RegexPatterns.LINE_NUMBER, error_output)
        line_number = int(line_match.group(1)) if line_match else None
        
        # Advanced IndexError analysis
        error_type, suggestion = self._analyze_index_error(error_output)
        
        return ErrorDetails(
            error_type=error_type, 
            line_number=line_number, 
            suggestion=suggestion,
            extra_data={MetadataKey.ERROR_OUTPUT.value: error_output}
        )
    
    def _analyze_index_error(self, error_output: str) -> Tuple[str, str]:
        """Advanced analysis of IndexError patterns"""
        if "list index out of range" in error_output:
            return "list_index_out_of_range", "Add bounds checking for list access"
        elif "string index out of range" in error_output:
            return "string_index_out_of_range", "Add bounds checking for string access"
        elif "tuple index out of range" in error_output:
            return "tuple_index_out_of_range", "Add bounds checking for tuple access"
        elif "pop from empty list" in error_output:
            return "empty_list_pop", "Check if list is not empty before pop()"
        else:
            return "general_index", "Add bounds checking for sequence access"
    
    def fix_error(self, script_path: str, details: ErrorDetails) -> bool:
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if not details.line_number or details.line_number > len(lines):
                return False
            
            line_idx = details.line_number - 1
            current_line = lines[line_idx]
            fixed_line = self._apply_index_fix(current_line, details)
            
            if fixed_line != current_line:
                lines[line_idx] = fixed_line
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                logger.info(f"Fixed IndexError on line {details.line_number}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to fix IndexError: {e}")
            return False
    
    def _apply_index_fix(self, line: str, details: ErrorDetails) -> str:
        """Apply specific fixes based on IndexError type"""
        error_type = details.error_type
        
        if error_type == SyntaxErrorSubType.EMPTY_LIST_POPERROR.value:
            # Fix empty list pop
            line = re.sub(RegexPatterns.EMPTY_LIST_POP, r'\1.pop() if \1 else None', line)
            return line
        
        # Find sequence access patterns and add bounds checking
        access_patterns = [
            RegexPatterns.INDEX_ACCESS,  # Basic indexing
            RegexPatterns.NEGATIVE_INDEXING,    # Negative indexing
        ]
        
        for pattern in access_patterns:
            matches = re.findall(pattern, line)
            for obj_name, index_expr in matches:
                unsafe_access = f"{obj_name}[{index_expr}]"
                
                if index_expr.lstrip('-').isdigit():
                    # Numeric index
                    idx = int(index_expr)
                    if idx >= 0:
                        safe_access = f"({obj_name}[{index_expr}] if len({obj_name}) > {index_expr} else None)"
                    else:
                        safe_access = f"({obj_name}[{index_expr}] if len({obj_name}) >= {abs(idx)} else None)"
                else:
                    # Variable index
                    safe_access = f"({obj_name}[{index_expr}] if 0 <= {index_expr} < len({obj_name}) else None)"
                
                line = line.replace(unsafe_access, safe_access)
        
        return line
    
    @property
    def error_name(self) -> str:
        return INDEX_ERROR.to_string()

class SyntaxErrorHandler(ErrorHandler):
    def __init__(self):
        self.unified_handler = create_syntax_error_handler()
    
    def can_handle(self, error_output: str) -> bool:
        return self.unified_handler.can_handle(error_output)
    
    def extract_details(self, error_output: str) -> ErrorDetails:
        error_type, suggestion, details = self.unified_handler.analyze_error(error_output)
        
        return ErrorDetails(
            error_type=error_type.value,
            line_number=details.get(MetadataKey.LINE_NUMBER.value),
            suggestion=suggestion,
            extra_data=details
        )
    
    def fix_error(self, script_path: str, details: ErrorDetails) -> bool:
        error_type = SyntaxErrorType(details.error_type)
        return self.unified_handler.apply_syntax_fix(script_path, error_type, details.extra_data)
    
    def error_name(self) -> str:
        return SYNTAX_ERROR.to_string()

class AutoFixer:
    """Main AutoFixer class that orchestrates error detection and fixing"""
    
    def __init__(self):
        self.handlers = {
            MODULE_NOT_FOUND: ModuleNotFoundErrorHandler(),
            TYPE_ERROR: TypeErrorHandler(),
            INDENTATION_ERROR: IndentationErrorHandler(),
            INDEX_ERROR: IndexErrorHandler(),
            SYNTAX_ERROR: SyntaxErrorHandler(),
            TAB_ERROR: TabErrorHandler()
        }
        self.error_parser = ErrorParser()
    
    def run_script(self, script_path: str) -> Tuple[bool, Optional[subprocess.CalledProcessError]]:
        """Run script with loading spinner"""
        logger.info(f"INFO: Running script: {script_path}")

        try:
            with spinner("Running"):
                result = subprocess.run([sys.executable, script_path], check=True)
            logger.info("Script executed successfully!")
            return True, None
        except subprocess.CalledProcessError as e:
            logger.error(f"Script failed with error: {e}")
            return False, e
        except FileNotFoundError:
            logger.error(f"ERROR: File not found: {script_path}")
            print(f"ERROR: Script file not found: {script_path}")
            return False, None

    
    def find_handler(self, error_output: str) -> Optional[ErrorHandler]:
        """Find appropriate handler for the error"""
        for handler in self.handlers.values():
            if handler.can_handle(error_output):
                return handler
        return None
    
    def _convert_bool_to_int(self, obj):
        """Convert boolean values to integers for Firebase compatibility"""
        if isinstance(obj, dict):
            return {k: self._convert_bool_to_int(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_bool_to_int(v) for v in obj]
        elif isinstance(obj, bool):
            return int(obj)
        return obj

    def save_metrics(self, script_path: str, status: str, **kwargs):
        print(f'DEBUG METRICS: Calling save_metrics for {script_path}, status={status}, ENABLED={METRICS_ENABLED}')
        if not METRICS_ENABLED or not metrics_collector:
            return False
        
        try:
            original_error = kwargs.get('original_error')
            error_details = kwargs.get('error_details', {})
            message = kwargs.get('message', f"Status: {status}")
            fix_attempts = kwargs.get('fix_attempts', 0)
            fix_duration = kwargs.get('fix_duration', 0.0)

            app_id = os.getenv('APP_ID', EnvironmentVariables.DEFAULT_APP_ID)
            error_details['app_id'] = app_id

            kwargs = self._convert_bool_to_int(kwargs)
            error_details = self._convert_bool_to_int(error_details)

            success = metrics_collector.save_metrics(
                script_path=script_path,
                status=status,
                original_error=original_error,
                error_details=error_details,
                message=message,
                fix_attempts=fix_attempts,
                fix_duration=fix_duration,
                **{k: v for k, v in kwargs.items() if k not in ['original_error', 'error_details', 'message', 'fix_attempts', 'fix_duration']}
            )

            return success
            
        except Exception as e:
            logger.debug(f"Metrics save failed silently: {e}")
            return False 

    
    def process_script(self, script_path: str, max_retries: int = 3, auto_fix: bool = False) -> bool:
        """Enhanced main processing logic with ErrorParser integration and retry mechanism"""
        if not os.path.exists(script_path):
            logger.error(f"Script not found: {script_path}")
            print(f"ERROR: Script not found: {script_path}")
            return False

        retry_attempts = 0
        start_time = time.time()
        
        while retry_attempts <= max_retries:
            success, error = self.run_script(script_path)

            if success:
                duration = time.time() - start_time
                logger.info("Script ran successfully with no errors.")
                print("INFO: Script ran successfully with no errors.")
                self.save_metrics(
                    script_path=script_path,
                    status=FixStatus.SUCCESS.value,
                    message="Script executed without errors",
                    fix_attempts=retry_attempts,
                    fix_duration=duration
                )
                return True

            if not error:
                logger.error("Unknown error occurred.")
                print("INFO: Unknown error occurred.")
                self.save_metrics(
                    script_path=script_path,
                    status=FixStatus.FAILURE.value,
                    original_error=FixStatus.UNKNOWN.value, 
                    message="Unknown error occurred during execution",
                    fix_attempts=retry_attempts
                )
                return False

            # Enhanced error analysis using ErrorParser
            parsed_error = self.error_parser.parse_error(error.stderr)
            handler = self.find_handler(error.stderr)

            if not handler:
                logger.info("Error type not supported for automatic fixing.")
                print("INFO: Error type not supported for automatic fixing.")
                print("Full error output:")
                print(error.stderr)
                
                # Enhanced metrics with parsed error context
                error_details = {
                    "stderr": error.stderr[:500],
                    "parsed_error_type": parsed_error.error_type if parsed_error else "unknown",
                    "file_path": parsed_error.file_path if parsed_error else None,
                    MetadataKey.LINE_NUMBER.value: parsed_error.line_number if parsed_error else None
                }
                
                self.save_metrics(
                    script_path=script_path,
                    status=FixStatus.UNSUPPORTED_ERROR.value,
                    error_details=error_details,
                    message="Error type not supported for automatic fixing",
                    fix_attempts=retry_attempts
                )
                return False

            # Extract details using both handler and parsed error context
            details = handler.extract_details(error.stderr)
            
            # Enhance details with parsed error information
            if parsed_error:
                details.extra_data = details.extra_data or {}
                details.extra_data.update({
                    "parsed_error": parsed_error,
                    "confidence": parsed_error.confidence,
                    "suggested_fix": parsed_error.suggested_fix
                })

            # Enhanced user feedback with better context
            print(f"INFO: Detected error: {handler.error_name}")
            print(f"INFO: {details.suggestion}")
            if details.line_number:
                print(f"INFO: Error on line {details.line_number}")
            if parsed_error and parsed_error.confidence:
                print(f"INFO: Fix confidence: {parsed_error.confidence:.1%}")

            if auto_fix:
                user_confirmed = True
                logger.info("Auto-fix enabled; automatically approving fix.")
                print("INFO: Auto-fix enabled; automatically approving fix.")
            else:
                user_input = input(f"ACTION REQUIRED: Fix the {handler.error_name}? (y/n): ").strip().lower()
                user_confirmed = user_input in ('y', 'yes')

            if not user_confirmed:
                logger.info("Fix canceled by user.")
                print("INFO: Fix canceled by user.")
                
                error_details = {
                    "error_type": details.error_type,
                    MetadataKey.LINE_NUMBER.value: details.line_number,
                    "parsed_error_type": parsed_error.error_type if parsed_error else None,
                    "confidence": parsed_error.confidence if parsed_error else None
                }
                
                self.save_metrics(
                    script_path=script_path,
                    status=FixStatus.CANCELED.value,
                    original_error=handler.error_name,
                    error_details=error_details,
                    message=f"User canceled {handler.error_name} fix",
                    fix_attempts=retry_attempts
                )
                return False

            logger.info(f"Attempting to fix {handler.error_name}, Attempt {retry_attempts + 1} of {max_retries + 1}")
            print(f"Attempting to fix {handler.error_name}, Attempt {retry_attempts + 1} of {max_retries + 1}")

            if not script_path:
                logger.error("Cannot fix error: script_path is None or empty")
                return False


            fix_successful = handler.fix_error(script_path, details)
            
            if fix_successful:
                retry_attempts += 1
                logger.info(f"{handler.error_name} fixed. Retrying script execution (Attempt {retry_attempts})...")
                print(f"{handler.error_name} fixed. Retrying script execution...")
                
                duration = time.time() - start_time
                self.save_metrics(
                    script_path=script_path,
                    status=FixStatus.FIX_APPLIED.value,
                    original_error=handler.error_name,
                    error_details={
                        "error_type": details.error_type,
                        MetadataKey.LINE_NUMBER.value: details.line_number,
                        "fix_applied": "true",
                        "confidence": parsed_error.confidence if parsed_error else None
                    },
                    message=f"Successfully applied fix for {handler.error_name}",
                    fix_attempts=retry_attempts,
                    fix_duration=duration
                )
            else:
                logger.error(f"Failed to fix {handler.error_name} on attempt {retry_attempts + 1}.")
                print(f"ERROR: Failed to automatically fix {handler.error_name} on attempt {retry_attempts + 1}.")
                
                error_details = {
                    "error_type": details.error_type,
                    MetadataKey.LINE_NUMBER.value: details.line_number,
                    "fix_applied": "false",
                    "parsed_error_type": parsed_error.error_type if parsed_error else None,
                    "confidence": parsed_error.confidence if parsed_error else None
                }
                
                self.save_metrics(
                    script_path=script_path,
                    status=FixStatus.FAILURE.value,
                    original_error=handler.error_name,
                    error_details=error_details,
                    message=f"Failed to apply fix for {handler.error_name}",
                    fix_attempts=retry_attempts
                )
                return False

        duration = time.time() - start_time
        logger.error(f"Exceeded max retries ({max_retries}) for script {script_path}. Fix failed.")
        print(f"ERROR: Exceeded max retries ({max_retries}). Fix failed.")
        
        self.save_metrics(
            script_path=script_path,
            status=FixStatus.MAX_RETRIES_EXCEEDED.value,
            original_error=handler.error_name if 'handler' in locals() else FixStatus.UNKNOWN.value,
            message="Maximum retry attempts exceeded",
            fix_attempts=retry_attempts,
            fix_duration=duration
        )
        return False

def main():
    """Main entry point with command-line argument parsing"""
    parser = create_parser()
    args = parser.parse_args(sys.argv[1:])

    # Handle no script path - MOVE THIS TO THE TOP
    if not args.script_path:
        parser.print_help()
        sys.exit(1)

    # Validate arguments
    error_msg = validate_args(args)
    if error_msg:
        print(error_msg)
        if error_msg.startswith("Error:"):
            sys.exit(1)

    logger = quick_setup(verbose=args.verbose > 0, quiet=args.quiet)
    logger.info(f"Starting AutoFix for: {args.script_path}")
    logger.debug(f"Verbosity level: {args.verbose}")

    if not validate_script_path(args.script_path, logger):
        sys.exit(1)

    config = {
        'interactive': True,
        'auto_install': args.auto_install,
        'max_retries': args.max_retries,
        'create_files': True,
        'dry_run': False
    }

    fixer = PythonFixer(config=config)
    
    # Track execution with metrics
    start_time = time.time()
    success = fixer.run_script_with_fixes(args.script_path)
    duration = time.time() - start_time
    
    # Save metrics after execution
    if METRICS_ENABLED and metrics_collector:
        status = 'success' if success else 'failure'
        metrics_collector.save_metrics(
            script_path=args.script_path,
            status=status,
            message=f'Script executed: {status}',
            fix_duration=duration
        )
        logger.debug(f'Metrics saved: {status} for {args.script_path}')
    

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

    
