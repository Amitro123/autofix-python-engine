import subprocess
import sys
import os
import re
import threading
import time
import json
import argparse
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timezone
from logging_utils import get_logger
from error_parser import ErrorParser, ParsedError
from import_suggestions import (
    IMPORT_SUGGESTIONS, STDLIB_MODULES, MULTI_IMPORT_SUGGESTIONS,
    KNOWN_PIP_PACKAGES, MATH_FUNCTIONS, MODULE_TO_PACKAGE
)

logger = get_logger("autofix_cli_interactive")

# Firebase Admin SDK for production metrics (transparent to users)
try:
    from .firestore_client import get_metrics_collector
    metrics_collector = get_metrics_collector()
    METRICS_ENABLED = metrics_collector.client is not None

    if METRICS_ENABLED:
        __app_id = metrics_collector.app_id
    else:
        __app_id = "autofix-default-app"


except ImportError as e:
    metrics_collector = None  
    METRICS_ENABLED = False
    __app_id = "autofix-default-app"
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

class ModuleNotFoundHandler(ErrorHandler):
    def can_handle(self, error_output: str) -> bool:
        return "ModuleNotFoundError" in error_output
    
    def extract_details(self, error_output: str) -> ErrorDetails:
        # Extract module name from "No module named 'module_name'"
        match = re.search(r"No module named ['\"]([^'\"]+)['\"]", error_output)
        module_name = match.group(1) if match else None
        
        line_match = re.search(r'line (\d+)', error_output)
        line_number = int(line_match.group(1)) if line_match else None
        
        suggestion = self._get_advanced_suggestion(module_name) if module_name else "Check module name and installation"
        
        return ErrorDetails(
            error_type="module_not_found",
            line_number=line_number,
            suggestion=suggestion,
            extra_data={"module_name": module_name}
        )
    
    def _get_advanced_suggestion(self, module_name: str) -> str:
        """Get sophisticated suggestion based on module name analysis"""
        # Check if it's a known pip package
        if module_name in KNOWN_PIP_PACKAGES:
            return f"Install pip package: pip install {module_name}"
        
        # Check for common package name variations
        package_name = self._resolve_package_name(module_name)
        if package_name and package_name != module_name:
            return f"Install pip package: pip install {package_name} (for module {module_name})"
        
        # Check if this looks like a test module
        if self._is_likely_test_module(module_name):
            return f"Module '{module_name}' appears to be a test/placeholder. Consider using a real package name or creating a local module."
        
        return f"Install missing module: pip install {module_name}"
    
    def _resolve_package_name(self, module_name: str) -> Optional[str]:
        """Resolve module name to actual package name"""
        # Check MODULE_TO_PACKAGE mapping
        if module_name in MODULE_TO_PACKAGE:
            return MODULE_TO_PACKAGE[module_name]
        
        # Common variations
        variations = {
            'cv2': 'opencv-python',
            'PIL': 'Pillow',
            'sklearn': 'scikit-learn',
            'yaml': 'PyYAML',
            'bs4': 'beautifulsoup4',
            'dateutil': 'python-dateutil'
        }
        
        return variations.get(module_name)
    
    def _is_likely_test_module(self, module_name: str) -> bool:
        """Check if module name looks like a test/placeholder"""
        test_patterns = [
            r'test[_\d]*',
            r'example[_\d]*',
            r'demo[_\d]*',
            r'placeholder[_\d]*',
            r'nonexistent[_\d]*',
            r'fake[_\d]*',
            r'dummy[_\d]*'
        ]
        
        for pattern in test_patterns:
            if re.match(pattern, module_name.lower()):
                return True
        return False
    
    def fix_error(self, script_path: str, details: ErrorDetails) -> bool:
        module_name = details.extra_data.get("module_name")
        if not module_name:
            return False
        
        # Check if it's a test module - don't try to install
        if self._is_likely_test_module(module_name):
            logger.warning(f"Skipping installation of test module: {module_name}")
            return self._create_local_module(module_name, script_path)
        
        # Try to resolve package name
        package_name = self._resolve_package_name(module_name) or module_name
        
        try:
            # Try to install the package
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package_name],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully installed {package_name}")
                return True
            else:
                logger.warning(f"Failed to install {package_name}: {result.stderr}")
                # Try creating a local module as fallback
                return self._create_local_module(module_name, script_path)
                
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            logger.error(f"Error installing {package_name}: {e}")
            return self._create_local_module(module_name, script_path)
    
    def _create_local_module(self, module_name: str, script_path: str) -> bool:
        """Create a basic local module file"""
        try:
            script_dir = os.path.dirname(script_path)
            module_file = os.path.join(script_dir, f"{module_name}.py")
            
            if not os.path.exists(module_file):
                with open(module_file, 'w', encoding='utf-8') as f:
                    f.write(f'"""\n{module_name} - Auto-generated module\n"""\n\n')
                    f.write('# Add your module content here\n')
                    f.write('pass\n')
                
                logger.info(f"Created local module: {module_file}")
                return True
            
            return True
        except Exception as e:
            logger.error(f"Failed to create local module {module_name}: {e}")
            return False
    
    @property
    def error_name(self) -> str:
        return "ModuleNotFoundError"

class TypeErrorHandler(ErrorHandler):
    def can_handle(self, error_output: str) -> bool:
        return "TypeError" in error_output
    
    def extract_details(self, error_output: str) -> ErrorDetails:
        line_matches = re.findall(r'line (\d+)', error_output)
        line_number = int(line_matches[-2] if len(line_matches) > 1 else line_matches[0]) if line_matches else None
        
        # Advanced TypeError pattern matching
        error_type, suggestion = self._analyze_type_error(error_output)
        
        return ErrorDetails(
            error_type=error_type, 
            line_number=line_number, 
            suggestion=suggestion,
            extra_data={"error_output": error_output}
        )
    
    def _analyze_type_error(self, error_output: str) -> Tuple[str, str]:
        """Advanced analysis of TypeError patterns"""
        # Unsupported operand types
        if "unsupported operand type" in error_output or "can only concatenate" in error_output:
            return "unsupported_operand", "Fix type mismatch in operation (add type conversion)"
        
        # Function argument issues
        if "takes" in error_output and "positional argument" in error_output:
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
        
        if error_type == 'unsupported_operand':
            # Fix string + number concatenation
            line = re.sub(r'(["\'][^"\']*["\'])\s*\+\s*(\d+)', r'\1 + str(\2)', line)
            line = re.sub(r'(\d+)\s*\+\s*(["\'][^"\']*["\'])', r'str(\1) + \2', line)
            line = re.sub(r'(\w+)\s*\+\s*(\d+)', r'\1 + str(\2)', line)
            
            # Fix list + string issues
            line = re.sub(r'(\[\w+\])\s*\+\s*(["\'][^"\']*["\'])', r'\1 + [\2]', line)
        
        elif error_type == 'not_iterable':
            # Add list conversion for common cases
            if 'for' in line and 'in' in line:
                # Convert: for x in variable -> for x in [variable] if variable is not iterable
                line = re.sub(r'for\s+(\w+)\s+in\s+(\w+)(?!\[)', r'for \1 in [\2] if isinstance(\2, (list, tuple)) else \2', line)
        
        elif error_type == 'not_subscriptable':
            # Convert indexing to attribute access where appropriate
            line = re.sub(r'(\w+)\[(\d+)\]', r'getattr(\1, "item_\2", None)', line)
        
        return line
    
    @property
    def error_name(self) -> str:
        return "TypeError"

class IndentationErrorHandler(ErrorHandler):
    def can_handle(self, error_output: str) -> bool:
        return "IndentationError" in error_output
    
    def extract_details(self, error_output: str) -> ErrorDetails:
        line_match = re.search(r'line (\d+)', error_output)
        line_number = int(line_match.group(1)) if line_match else None
        
        if "expected an indented block" in error_output:
            error_type = "missing_indentation"
            suggestion = "Add proper indentation to the code block"
        elif "unindent does not match" in error_output:
            error_type = "inconsistent_indentation"
            suggestion = "Fix inconsistent indentation"
        elif "unexpected indent" in error_output:
            error_type = "unexpected_indent"
            suggestion = "Remove unnecessary indentation"
        else:
            error_type = "general_indentation"
            suggestion = "Fix indentation issues"
        
        return ErrorDetails(error_type=error_type, line_number=line_number, suggestion=suggestion)
    
    def fix_error(self, script_path: str, details: ErrorDetails) -> bool:
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if details.error_type == 'missing_indentation' and details.line_number:
                line_idx = details.line_number - 1
                if line_idx < len(lines):
                    current_line = lines[line_idx].strip()
                    if current_line:
                        # Add 4 spaces indentation
                        lines[line_idx] = '    ' + current_line + '\n'
            elif details.error_type == 'inconsistent_indentation':
                # Convert tabs to spaces
                lines = [line.expandtabs(4) for line in lines]
            elif details.error_type == 'unexpected_indent' and details.line_number:
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
        return "IndentationError"

class IndexErrorHandler(ErrorHandler):
    def can_handle(self, error_output: str) -> bool:
        return "IndexError" in error_output
    
    def extract_details(self, error_output: str) -> ErrorDetails:
        line_match = re.search(r'line (\d+)', error_output)
        line_number = int(line_match.group(1)) if line_match else None
        
        # Advanced IndexError analysis
        error_type, suggestion = self._analyze_index_error(error_output)
        
        return ErrorDetails(
            error_type=error_type, 
            line_number=line_number, 
            suggestion=suggestion,
            extra_data={"error_output": error_output}
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
        
        if error_type == "empty_list_pop":
            # Fix empty list pop
            line = re.sub(r'(\w+)\.pop\(\)', r'\1.pop() if \1 else None', line)
            return line
        
        # Find sequence access patterns and add bounds checking
        access_patterns = [
            r'(\w+)\[(\w+|\d+)\]',  # Basic indexing
            r'(\w+)\[(-?\d+)\]',    # Negative indexing
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
        return "IndexError"

class SyntaxErrorHandler(ErrorHandler):
    def can_handle(self, error_output: str) -> bool:
        return "SyntaxError" in error_output
    
    def extract_details(self, error_output: str) -> ErrorDetails:
        line_match = re.search(r'line (\d+)', error_output)
        line_number = int(line_match.group(1)) if line_match else None
        
        # Advanced SyntaxError analysis
        error_type, suggestion = self._analyze_syntax_error(error_output)
        
        return ErrorDetails(
            error_type=error_type,
            line_number=line_number,
            suggestion=suggestion,
            extra_data={"error_output": error_output}
        )
    
    def _analyze_syntax_error(self, error_output: str) -> Tuple[str, str]:
        """Advanced analysis of SyntaxError patterns"""
        if "invalid syntax" in error_output:
            if "(" in error_output or ")" in error_output:
                return "parentheses_mismatch", "Check for missing or extra parentheses"
            elif ":" in error_output:
                return "missing_colon", "Add missing colon after if/for/while/def/class statements"
            else:
                return "invalid_syntax", "Fix syntax error - check keywords and punctuation"
        elif "unexpected EOF" in error_output:
            return "unexpected_eof", "Missing closing parentheses, brackets, or quotes"
        elif "invalid character" in error_output:
            return "invalid_character", "Remove invalid characters or fix encoding issues"
        elif "indentation" in error_output.lower():
            return "indentation_syntax", "Fix indentation - use consistent spaces or tabs"
        else:
            return "general_syntax", "Fix syntax error - check Python syntax rules"
    
    def fix_error(self, script_path: str, details: ErrorDetails) -> bool:
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            fixed_content = self._apply_syntax_fixes(content, details)
            
            if fixed_content != original_content:
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                logger.info(f"Fixed SyntaxError on line {details.line_number}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to fix SyntaxError: {e}")
            return False
    
    def _apply_syntax_fixes(self, content: str, details: ErrorDetails) -> str:
        """Apply specific syntax fixes based on error type"""
        error_type = details.error_type
        
        # Fix common broken keywords
        keyword_fixes = {
            r'\bi f\b': 'if', r'\bd ef\b': 'def', r'\bc lass\b': 'class',
            r'\be lse\b': 'else', r'\be lif\b': 'elif', r'\bf or\b': 'for',
            r'\bw hile\b': 'while', r'\bt ry\b': 'try', r'\be xcept\b': 'except',
            r'\bf rom\b': 'from', r'\bi mport\b': 'import', r'\br eturn\b': 'return'
        }
        
        for pattern, replacement in keyword_fixes.items():
            content = re.sub(pattern, replacement, content)
        
        if error_type == "missing_colon":
            # Add missing colons after control structures
            content = re.sub(r'\b(if|elif|else|for|while|def|class|try|except|finally|with)\s+[^:\n]*(?<![:\n])\s*$', r'\g<0>:', content, flags=re.MULTILINE)
        
        elif error_type == "parentheses_mismatch":
            # Basic parentheses balancing
            lines = content.split('\n')
            for i, line in enumerate(lines):
                open_count = line.count('(')
                close_count = line.count(')')
                if open_count > close_count:
                    lines[i] = line + ')' * (open_count - close_count)
                elif close_count > open_count and i > 0:
                    lines[i-1] = lines[i-1] + '(' * (close_count - open_count)
            content = '\n'.join(lines)
        
        elif error_type == "unexpected_eof":
            # Add missing closing characters
            if content.count('"') % 2 == 1:
                content += '"'
            if content.count("'") % 2 == 1:
                content += "'"
            if content.count('(') > content.count(')'):
                content += ')' * (content.count('(') - content.count(')'))
            if content.count('[') > content.count(']'):
                content += ']' * (content.count('[') - content.count(']'))
            if content.count('{') > content.count('}'):
                content += '}' * (content.count('{') - content.count('}'))
        
        return content
    
    @property
    def error_name(self) -> str:
        return "SyntaxError"

class AutoFixer:
    """Main AutoFixer class that orchestrates error detection and fixing"""
    
    def __init__(self):
        self.handlers = [
            ModuleNotFoundHandler(),
            TypeErrorHandler(),
            IndentationErrorHandler(),
            IndexErrorHandler(),
            SyntaxErrorHandler()
        ]
        self.error_parser = ErrorParser()
        self.import_suggestions = IMPORT_SUGGESTIONS
        self.stdlib_modules = STDLIB_MODULES
        self.known_pip_packages = KNOWN_PIP_PACKAGES
    
    def run_script(self, script_path: str) -> Tuple[bool, Optional[subprocess.CalledProcessError]]:
        """Run script with loading spinner"""
        logger.info(f"INFO: Running script: {script_path}")
        
        spinner_event = threading.Event()
        spinner_thread = threading.Thread(target=self._loading_spinner, args=(spinner_event,))
        spinner_thread.start()

        try:
            result = subprocess.run([sys.executable, script_path], 
                                 capture_output=True, text=True, check=True)
            spinner_event.set()
            spinner_thread.join()
            print("\r" + " " * 30 + "\r", end="")
            logger.info(f"Script output: {result.stdout.strip()}")
            return True, None
        except subprocess.CalledProcessError as e:
            spinner_event.set()
            spinner_thread.join()
            print("\r" + " " * 30 + "\r", end="")
            logger.error(f"Script failed with error: {e.stderr.strip()}")
            return False, e
        except FileNotFoundError:
            spinner_event.set()
            spinner_thread.join()
            logger.error(f"ERROR: File not found: {script_path}")
            print(f"ERROR: Script file not found: {script_path}")
            return False, None
    
    def _loading_spinner(self, stop_event):
        """Console spinner for progress indication"""
        spinner = ['|', '/', '-', '\\']
        i = 0
        while not stop_event.is_set():
            sys.stdout.write(f"\r  Running... {spinner[i % len(spinner)]}")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
    
    def find_handler(self, error_output: str) -> Optional[ErrorHandler]:
        """Find appropriate handler for the error"""
        for handler in self.handlers:
            if handler.can_handle(error_output):
                return handler
        return None
    
    def save_metrics(self, script_path: str, status: str, **kwargs):
        if not METRICS_ENABLED or not metrics_collector:
            return False
        
        try:
            # Extract parameters from kwargs (since metrics_collector.save_metrics expects them separately)
            original_error = kwargs.get('original_error')
            error_details = kwargs.get('error_details', {})
            message = kwargs.get('message', f"Status: {status}")
            fix_attempts = kwargs.get('fix_attempts', 0)
            fix_duration = kwargs.get('fix_duration', 0.0)

            # Add dynamic app_id to error_details for context
            app_id = os.getenv('APP_ID', 'autofix-default-app')
            error_details['app_id'] = app_id

            # Use the unified metrics collector from firestore_client.py
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

            if success:
                logger.info(f"Saved metrics: {status} for script {script_path}")
            else:
                logger.debug(f"Failed to save metrics for script {script_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to save metrics to Firebase: {e}")
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
                    status="success",
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
                    status="failure",
                    original_error="Unknown",
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
                    "line_number": parsed_error.line_number if parsed_error else None
                }
                
                self.save_metrics(
                    script_path=script_path,
                    status="unsupported_error",
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
                
                # Enhanced metrics with parsed error context
                error_details = {
                    "error_type": details.error_type,
                    "line_number": details.line_number,
                    "parsed_error_type": parsed_error.error_type if parsed_error else None,
                    "confidence": parsed_error.confidence if parsed_error else None
                }
                
                self.save_metrics(
                    script_path=script_path,
                    status="canceled",
                    original_error=handler.error_name,
                    error_details=error_details,
                    message=f"User canceled {handler.error_name} fix",
                    fix_attempts=retry_attempts
                )
                return False

            logger.info(f"Attempting to fix {handler.error_name}, Attempt {retry_attempts + 1} of {max_retries + 1}")
            print(f"Attempting to fix {handler.error_name}, Attempt {retry_attempts + 1} of {max_retries + 1}")

            # Apply fix with enhanced context
            fix_successful = handler.fix_error(script_path, details)
            
            if fix_successful:
                retry_attempts += 1
                logger.info(f"{handler.error_name} fixed. Retrying script execution (Attempt {retry_attempts})...")
                print(f"{handler.error_name} fixed. Retrying script execution...")
                
                # Save successful fix metrics
                duration = time.time() - start_time
                self.save_metrics(
                    script_path=script_path,
                    status="fix_applied",
                    original_error=handler.error_name,
                    error_details={
                        "error_type": details.error_type,
                        "line_number": details.line_number,
                        "fix_applied": True,
                        "confidence": parsed_error.confidence if parsed_error else None
                    },
                    message=f"Successfully applied fix for {handler.error_name}",
                    fix_attempts=retry_attempts,
                    fix_duration=duration
                )
            else:
                logger.error(f"Failed to fix {handler.error_name} on attempt {retry_attempts + 1}.")
                print(f"ERROR: Failed to automatically fix {handler.error_name} on attempt {retry_attempts + 1}.")
                
                # Enhanced failure metrics
                error_details = {
                    "error_type": details.error_type,
                    "line_number": details.line_number,
                    "fix_applied": False,
                    "parsed_error_type": parsed_error.error_type if parsed_error else None,
                    "confidence": parsed_error.confidence if parsed_error else None
                }
                
                self.save_metrics(
                    script_path=script_path,
                    status="fix_failed",
                    original_error=handler.error_name,
                    error_details=error_details,
                    message=f"Failed to apply fix for {handler.error_name}",
                    fix_attempts=retry_attempts
                )
                return False

        # If we've exceeded max retries
        duration = time.time() - start_time
        logger.error(f"Exceeded max retries ({max_retries}) for script {script_path}. Fix failed.")
        print(f"ERROR: Exceeded max retries ({max_retries}). Fix failed.")
        
        self.save_metrics(
            script_path=script_path,
            status="max_retries_exceeded",
            original_error=handler.error_name if 'handler' in locals() else "Unknown",
            message="Maximum retry attempts exceeded",
            fix_attempts=retry_attempts,
            fix_duration=duration
        )
        return False

def main():
    """Main entry point with command-line argument parsing"""
    parser = argparse.ArgumentParser(description="AutoFix Interactive CLI")
    parser.add_argument("script_path", help="Path to the Python script to fix")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum number of fix retry attempts (default: 3)")
    parser.add_argument("--auto-fix", action="store_true", help="Automatically apply fixes without asking for confirmation")
    
    args = parser.parse_args()
    
    fixer = AutoFixer()
    success = fixer.process_script(args.script_path, max_retries=args.max_retries, auto_fix=args.auto_fix)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()