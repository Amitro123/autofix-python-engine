#!/usr/bin/env python3
"""
Python Fixer - Core Python error fixing logic

Handles automatic fixing of common Python errors including:
- ModuleNotFoundError (pip install, local file creation)
- ImportError (missing imports, function imports)
- NameError (undefined functions, variables)
- AttributeError (missing attributes, methods)
- SyntaxError (version compatibility issues)
- IndexError (list/array index out of bounds)
"""

import ast
import importlib
import os
import re
import runpy
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Callable
from .unified_syntax_handler import create_syntax_error_handler
from .import_suggestions import IMPORT_SUGGESTIONS, MATH_FUNCTIONS

from autofix.handlers.key_error_handler import KeyErrorHandler
from autofix.handlers.zero_division_handler import ZeroDivisionHandler
from autofix.handlers.index_error_handler import IndexErrorHandler
from autofix.handlers.import_error_handler import ImportErrorHandler
from .handlers.module_not_found_handler import (
    ModuleNotFoundHandler,
    ModuleValidation,
    PackageInstaller
)

# Handle both relative and absolute imports
try:
    from .constants import ErrorType
    from .error_parser import ErrorParser, ParsedError
    from .logging_utils import get_logger
    from .import_suggestions import ( #amitro changed
        IMPORT_SUGGESTIONS, STDLIB_MODULES, MULTI_IMPORT_SUGGESTIONS,
        KNOWN_PIP_PACKAGES, MATH_FUNCTIONS, MODULE_TO_PACKAGE
    )
except ImportError:
    # Fallback for direct execution
    from autofix.constants import ErrorType
    from error_parser import ErrorParser, ParsedError
    from logging_utils import get_logger
    from import_suggestions import (
        IMPORT_SUGGESTIONS, STDLIB_MODULES, MULTI_IMPORT_SUGGESTIONS,
        KNOWN_PIP_PACKAGES, MATH_FUNCTIONS, MODULE_TO_PACKAGE
    )

class PythonFixer:
    """Core Python error fixing functionality"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.auto_install = self.config.get('auto_install', False)
        self.create_files = self.config.get('create_files', True)
        self.max_retries = self.config.get('max_retries', 3)
        self.error_parser = ErrorParser()
        self.logger = get_logger("python_fixer")
        self.dry_run = self.config.get('dry_run', False)
              
    def analyze_potential_fixes(self, script_path: str) -> dict:
        """Analyze script and identify potential fixes without making changes"""
        results = {'script_path': script_path, 'errors_found': [], 'analysis_complete': True}
        
        try:
            self.logger.info(f"Analyzing script for potential fixes: {script_path}")
            runpy.run_path(script_path, run_name="__main__")
            self.logger.info("Script runs without errors - no fixes needed")
            return results
            
        except Exception as e:
            self.logger.info(f"Found error that would be fixed: {type(e).__name__}: {e}")
            parsed_error = self.error_parser.parse_exception(e, script_path)
            
            error_info = {
                'type': parsed_error.error_type,
                'message': str(e),
                'file_path': parsed_error.file_path,
                'line_number': parsed_error.line_number,
                'suggested_fixes': self._generate_fix_suggestions(parsed_error)
            }
            
            results['errors_found'].append(error_info)
            return results
    
    def _generate_fix_suggestions(self, error: ParsedError) -> list:
        """Generate fix suggestions based on error type"""
        error_type = ErrorType.from_string(error.error_type)
        
        if error_type == ErrorType.MODULE_NOT_FOUND:
            return self._suggest_module_fixes(error.missing_module)
        elif error_type == ErrorType.NAME_ERROR:
            return self._suggest_name_fixes(error.missing_function)
        elif error_type == ErrorType.IMPORT_ERROR:
            return self._suggest_import_fixes(error.missing_function, error.missing_module)
        elif error_type == ErrorType.SYNTAX_ERROR:
            return ["Fix syntax error automatically"]
        elif error_type == ErrorType.GENERAL_SYNTAX:
            return ["Fix general syntax error automatically"]
        else:
            return [f"Attempt to fix {error.error_type}"]
    
    def _suggest_module_fixes(self, module: str) -> list:
        """Generate suggestions for ModuleNotFoundError"""
        if not module:
            return []
        
        handler = ModuleNotFoundHandler()
        
        if module in handler.known_pip_packages:
            return [f"Install pip package: {module}"]
        
        package_name = ModuleValidation.resolve_package_name(module)
        if package_name and package_name != module:
            return [f"Install pip package: {package_name} (for module {module})"]
        
        return [f"Create local module file: {module}.py"]

    
    def _suggest_name_fixes(self, function: str) -> list:
        """Generate suggestions for NameError"""
        if not function:
            return []
        
        if function in self.common_imports:
            return [f"Add import: {self.common_imports[function]}"]
        elif function in self.math_functions:
            return [f"Add import: from math import {function}"]
        else:
            return [f"Create function: {function}()"]
    
    def _suggest_import_fixes(self, function: str, module: str) -> list:
        """Generate suggestions for ImportError"""
        if function and module:
            return [f"Add import: from {module} import {function}"]
        return []

    def run_script_with_fixes(self, script_path: str, recursion_depth: int = 0) -> bool:
        """
        Run Python script with automatic error fixing
        Args: script_path: Path to the Python script to execute
            recursion_depth: Current recursion depth to prevent infinite loops
        Returns:
            bool: True if script executed successfully, False otherwise
        """
        if recursion_depth > self.max_retries:
            self.logger.error(
                f"Maximum recursion depth ({self.max_retries}) reached. "
                "Stopping to prevent infinite loop."
            )
            return False
        
        try:
            # Save original working directory
            original_cwd = os.getcwd()
            script_dir = Path(script_path).parent
            os.chdir(script_dir)
            
            self.logger.info(f"Running script: {script_path}")
            runpy.run_path(script_path, run_name="__main__")
            self.logger.info("Script executed successfully!")
            return True
            
        except Exception as e:
            self.logger.info(f"Error detected: {type(e).__name__}: {e}")
            
            # Parse the error into structured format
            parsed_error = self.error_parser.parse_exception(e, script_path)
            
            # Attempt to fix the error
            if self.fix_parsed_error(parsed_error):
                self.logger.info("Error fixed, retrying script execution...")
                self._clear_module_cache(script_path)
                return self.run_script_with_fixes(script_path, recursion_depth + 1)
            else:
                if parsed_error.error_type == ErrorType.TYPE_ERROR.to_string():
                    self.logger.info(f"Provided suggestions for {parsed_error.error_type} - manual review required")
                    return True
                else:
                    self.logger.error(f"Could not auto-resolve {parsed_error.error_type}")
                return False
        finally:
            os.chdir(original_cwd)
    
    def fix_parsed_error(self, error: ParsedError) -> bool:
        """
        Fix a parsed error based on its type
        Args:
            error: Parsed error information
        Returns:
            bool: True if error was fixed, False otherwise
        """
        # Convert string error type to enum
        error_type = ErrorType.from_string(error.error_type)
        
        if not error_type:
            self.logger.warning(f"Unknown error type: {error.error_type}")
            return False

        # Use enum-based dispatch
        if error_type == ErrorType.MODULE_NOT_FOUND:
            return self._fix_module_not_found_error(error)
        elif error_type == ErrorType.IMPORT_ERROR:
            return self._fix_import_error(error)
        elif error_type == ErrorType.NAME_ERROR:
            return self._fix_name_error(error)
        elif error_type == ErrorType.ATTRIBUTE_ERROR:
            return self._fix_attribute_error(error)
        elif error_type == ErrorType.INDEX_ERROR:         
            return self._fix_index_error(error)            
        elif error_type == ErrorType.KEY_ERROR:
            return self._fix_key_error(error)
        elif error_type == ErrorType.ZERO_DIVISION_ERROR:  
            return self._fix_zero_division_error(error)    
        elif error_type == ErrorType.SYNTAX_ERROR:
            return self._fix_syntax_error(error)
        elif error_type == ErrorType.TYPE_ERROR:
            return self._fix_type_error(error)
        elif error_type == ErrorType.GENERAL_SYNTAX:
            return self._fix_syntax_error(error)
        else:
            self.logger.warning(f"No fix implementation for {error_type.to_string()}")
            return False

    def maybe_install_package(self, package_name: str) -> bool:
        """Install package using PackageInstaller"""
        if not self.auto_install:
            self.logger.info(f"Auto-install disabled. Please install manually: pip install {package_name}")
            return False
        
        installer = PackageInstaller(auto_install=True)
        return installer.install_package(package_name)

    def _fix_module_not_found_error(self, error: ParsedError) -> bool:
        """Fix ModuleNotFoundError - delegate to handler"""
        handler = ModuleNotFoundHandler(
            auto_install=self.auto_install,
            create_files=self.create_files
        )
        
        missing_module = error.missing_module
        if not missing_module:
            return False
        
        # Check for common package name variations
        package_name = ModuleValidation.resolve_package_name(missing_module)
        if package_name and package_name != missing_module:
            self.logger.info(f"Installing pip package: {package_name} (for module {missing_module})")
            return self.maybe_install_package(package_name)
        
        # Check if this looks like a real module name or just a test
        if ModuleValidation.is_likely_test_module(missing_module):
            self.logger.warning(f"Module '{missing_module}' appears to be a test/placeholder name")
            self.logger.info("Recommendations:")
            self.logger.info("  1. Replace with a real package name (e.g., 'requests', 'numpy', 'pandas')")
            self.logger.info("  2. Install a package: pip install <package-name>")
            self.logger.info("  3. Create a local module file if this is intentional")
            self.logger.info("  4. Comment out the import if it's just for testing")
            return False
        
        # Use handler to apply fix
        _, _, details = handler.analyze_error(error.error_message, error.file_path)
        return handler.apply_fix("ModuleNotFoundError", error.file_path, details)

    
    def _fix_name_error(self, error: ParsedError) -> bool:
        """Handle NameError - provide suggestions only (PARTIAL result)"""
        
        missing_name = error.missing_function or "unknown"

        print(f"\nNameError detected in {error.file_path}")
        print(f"Undefined name: '{missing_name}'")
        if error.line_number:
            print(f"Line: {error.line_number}")

        print("\nSuggestions:")

        if missing_name in IMPORT_SUGGESTIONS:
            print(f"  1. Add import: {IMPORT_SUGGESTIONS[missing_name]}")
            print(f"  2. Check variable spelling")
        # Check if it's a math function
        elif missing_name in MATH_FUNCTIONS:
            print(f"  1. Add import: from math import {missing_name}")
            print(f"  2. Define the function before use")
        else:
            print("  1. Check variable/function spelling")
            print("  2. Define variable before use")
            print("  3. Import missing module if needed")

        print("\nNameError requires manual review - PARTIAL result")
        return False  # PARTIAL - suggestions only, no auto-fix

    def _fix_import_error(self, error: ParsedError) -> bool:
        """Handle ImportError - delegate to ImportErrorHandler"""

        handler = ImportErrorHandler()
        _, _, details = handler.analyze_error(error.error_message, error.file_path)
        details['error_message'] = error.error_message
        
        return handler.apply_fix("ImportError", error.file_path, details)

     
    def _fix_index_error(self, error: ParsedError) -> bool:
        """
        Handle IndexError - provide suggestions only (PARTIAL result)
        
        IndexError is a runtime/logic error that cannot be auto-fixed.
        Provides targeted suggestions based on error subtype.
        
        Returns:
            bool: False (PARTIAL) - suggestions provided, manual review required
        """
        
        self.logger.info(f"IndexError detected: {error.error_message}")
        
        # Use handler for analysis and suggestions
        handler = IndexErrorHandler()
        _, _, details = handler.analyze_error(error.error_message, error.file_path)
        details['line_number'] = error.line_number
        
        # Handler will print suggestions and return False (PARTIAL)
        return handler.apply_fix("IndexError", error.file_path, details)


        
    def _fix_key_error(self, error: ParsedError) -> bool:
        """Handle KeyError - delegate to KeyErrorHandler"""
        handler = KeyErrorHandler()
        _, _, details = handler.analyze_error(error.error_message, error.file_path)
        details['error_message'] = error.error_message
        details['line_number'] = error.line_number

        return handler.apply_fix("KeyError", error.file_path, details)

    def _fix_zero_division_error(self, error: ParsedError) -> bool:
        """Handle ZeroDivisionError - delegate to ZeroDivisionHandler"""
        
        handler = ZeroDivisionHandler()
        _, _, details = handler.analyze_error(error.error_message, error.file_path)
        details['error_message'] = error.error_message
        details['line_number'] = error.line_number
        
        return handler.apply_fix("ZeroDivisionError", error.file_path, details)
   
    def _read_file_content(self, file_path: str) -> str:
        """Read file content with UTF-8 encoding"""
        return Path(file_path).read_text(encoding="utf-8")
    
    def _read_file_lines(self, file_path: str) -> list:
        """Read file and return lines"""
        content = self._read_file_content(file_path)
        return content.split('\n')
    
    def _validate_line_number(self, line_number: int, lines: list) -> Optional[int]:
        """Validate line number and return index"""
        if not line_number:
            self.logger.warning("No line number available for IndexError fix")
            return None
        
        line_idx = line_number - 1
        if line_idx >= len(lines):
            self.logger.warning("Line number out of range")
            return None
        
        return line_idx
    

    def _create_safe_access(self, list_name: str, index_expr: str, default_value: str) -> str:
        """Create safe access pattern for indexing"""
        if index_expr.isdigit():
            return f"{list_name}[{index_expr}] if len({list_name}) > {index_expr} else {default_value}"
        else:
            return f"{list_name}[{index_expr}] if {index_expr} < len({list_name}) else {default_value}"
    
    def _save_fixed_file(self, file_path: str, lines: list, fixes_applied: list) -> bool:
        """Save fixed file with backup"""
        backup_path = self._backup_file(file_path)
        self.logger.info(f"Created backup: {backup_path}")
        
        fixed_content = '\n'.join(lines)
        Path(file_path).write_text(fixed_content, encoding="utf-8")
        
        self.logger.info(f"Applied IndexError fixes: {', '.join(fixes_applied)}")
        return True
    
    def _backup_file(self, file_path: str) -> str:
        """Create backup before modifying file"""
        backup_path = f"{file_path}.autofix.bak"
        import shutil
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    def _create_function_in_script(self, function_name: str, script_path: str) -> bool:
        """Create a missing function directly in the script file"""
        try:
            if not self._validate_file_access(script_path):
                return False
            
            content = self._read_script_content(script_path)
            
            # Handle existing function (forward reference check)
            if self._function_exists(function_name, content):
                return self._handle_existing_function(function_name, script_path, content)
            
            # Generate and append new function
            function_code = self._generate_function_code(function_name, content)
            return self._append_function_to_file(script_path, content, function_code, function_name)
            
        except Exception as e:
            self.logger.error(f"Error creating function {function_name}: {e}")
            return False
    
    def _validate_file_access(self, script_path: str) -> bool:
        """Validate file exists and has write permissions"""
        script_file = Path(script_path)
        
        if not script_file.exists():
            return False
        
        if not os.access(script_file, os.W_OK):
            self.logger.error(f"No write permission for file: {script_file}")
            return False
        
        return True
    
    def _read_script_content(self, script_path: str) -> str:
        """Read script content and create backup"""
        self._backup_file(script_path)
        return self._read_file_content(script_path)
    
    def _function_exists(self, function_name: str, content: str) -> bool:
        """Check if function already exists in content"""
        return f"def {function_name}(" in content
    
    def _handle_existing_function(self, function_name: str, script_path: str, content: str) -> bool:
        """Handle case where function already exists (check forward references)"""
        self.logger.info(f"Function '{function_name}' already exists in {Path(script_path).name}")
        
        def_line, usage_line = self._find_function_positions(function_name, content)
        
        # If function is defined after first usage, move it to the top
        if def_line is not None and usage_line is not None and def_line > usage_line:
            self.logger.info(f"Moving function '{function_name}' to resolve forward reference")
            return self._move_function_to_top(function_name, script_path)
        
        return False
    
    def _find_function_positions(self, function_name: str, content: str) -> tuple:
        """Find function definition and first usage line numbers"""
        lines = content.split('\n')
        function_def_line = None
        first_usage_line = None
        
        for i, line in enumerate(lines):
            if f"def {function_name}(" in line and function_def_line is None:
                function_def_line = i
            if function_name in line and "def " not in line and first_usage_line is None:
                first_usage_line = i
        
        return function_def_line, first_usage_line
    
    def _generate_function_code(self, function_name: str, content: str) -> str:
        """Generate function code with intelligent parameter detection"""
        params = self._analyze_function_usage(function_name, content)
        param_str = ", ".join(params) if params else ""
        impl = self._generate_function_implementation(params)
        
        return f"""

def {function_name}({param_str}):
    \"\"\"Auto-generated function by AutoFix
    
    Parameters detected from usage analysis.
    TODO: Add proper implementation
    \"\"\"
    # Placeholder implementation based on usage context
    {impl}
"""
    
    def _generate_function_implementation(self, params: list) -> str:
        """Generate appropriate function implementation based on parameters"""
        if len(params) == 2:
            return f"return {params[0]} + {params[1]} if {params[0]} and {params[1]} else 0  # Basic calculation"
        elif len(params) == 1:
            return f"return len({params[0]}) if hasattr({params[0]}, '__len__') else {params[0]}"
        else:
            return "return 42  # Default return value"
    
    def _append_function_to_file(self, script_path: str, content: str, function_code: str, function_name: str) -> bool:
        """Append function code to file"""
        self.logger.info(f"Created missing function: {function_name}")
        
        new_content = content.rstrip() + function_code
        Path(script_path).write_text(new_content, encoding="utf-8")
        return True
    
    def _analyze_function_usage(self, function_name: str, content: str) -> List[str]:
        """Analyze how a function is used to infer parameters"""
        # Find function calls in the content
        call_pattern = rf"{re.escape(function_name)}\s*\(([^)]*)\)"
        calls = re.findall(call_pattern, content)
        
        params = []
        
        if calls:
            # Analyze the first call to infer parameters
            first_call = calls[0].strip()
            if first_call:
                # Smart argument parsing - handle nested structures
                arg_count = 0
                paren_depth = 0
                bracket_depth = 0
                current_arg = ""
                
                for char in first_call:
                    if char == '(':
                        paren_depth += 1
                    elif char == ')':
                        paren_depth -= 1
                    elif char == '[':
                        bracket_depth += 1
                    elif char == ']':
                        bracket_depth -= 1
                    elif char == ',' and paren_depth == 0 and bracket_depth == 0:
                        if current_arg.strip():
                            arg_count += 1
                        current_arg = ""
                        continue
                    
                    current_arg += char
                
                # Count the last argument
                if current_arg.strip():
                    arg_count += 1
                
                params = [f"arg{i + 1}" for i in range(arg_count)]
        
        return params
    
    def _fix_syntax_error(self, error: ParsedError) -> bool:
        """Fix SyntaxError using unified handler"""
        handler = create_syntax_error_handler()
        
        if handler.can_handle(error.error_message):
            error_type, suggestion, details = handler.analyze_error(
                error.error_message, 
                error.file_path
            )
            
            return handler.apply_syntax_fix(error.file_path, error_type, details)
        
        return False
    
    def _fix_attribute_error(self, error: ParsedError) -> bool:
        """Handle AttributeError - provide suggestions (PARTIAL result)"""
        print(f"\nAttributeError detected in {error.file_path}")
        
        # Extract attribute name if possible
        if "has no attribute" in error.error_message:
            # Try to extract: "module 'X' has no attribute 'Y'"
            parts = error.error_message.split("'")
            if len(parts) >= 4:
                module_name = parts[1]
                attr_name = parts[3]
                print(f"Module: {module_name}")
                print(f"Missing attribute: {attr_name}")
        
        if error.line_number:
            print(f"Line: {error.line_number}")
        
        print("\nSuggestions:")
        print("  1. Check object type and available methods")
        print("  2. Verify attribute/method name spelling")
        print("  3. Check documentation for deprecated methods")
        print("  4. Update to newer API if method is deprecated")
        
        # Specific suggestion for matplotlib.hold
        if "hold" in error.error_message and "matplotlib" in error.error_message:
            print("\nSpecific fix for matplotlib:")
            print("  plt.hold() was deprecated - remove this line")
            print("  Multiple plot calls are now held by default")
        
        print("\nAttributeError requires manual review - PARTIAL result")
        return False  # PARTIAL - suggestions only

    
    def _fix_type_error(self, error: ParsedError) -> bool:
        """Handle TypeError - provide suggestions only (PARTIAL result)"""
        print(f"\nTypeError detected in {error.file_path}")
        print(f"Error: {error.error_message}")
        if error.line_number:
            print(f"Line: {error.line_number}")
        
        print("\nSuggested fixes:")
        print("  1. Convert numbers to strings: str(number)")
        print("  2. Use f-strings: f'text{variable}'")  
        print("  3. Check variable types before operations")
        
        # Specific suggestions based on error message
        if "can only concatenate str" in error.error_message:
            print("String concatenation fix: result = 'hello' + str(5)")
        elif "unsupported operand" in error.error_message:
            print("Type mismatch fix: convert variables to same type")
        
        print("\nTypeError requires manual review - PARTIAL result")
        return False  # PARTIAL result - suggestions only
    
    def _fix_standard_library_import_error(self, error: ParsedError) -> bool:
        """Handle import errors from standard library modules by removing problematic imports"""
        try:
            content = self._read_file_content(error.file_path)
            lines = content.split('\n')

            script_file = Path(error.file_path)
            
            # Find and comment out the problematic import
            for i, line in enumerate(lines):
                if f"from {error.missing_module} import {error.missing_function}" in line:
                    lines[i] = f"# {line}  # Commented out by AutoFix - symbol does not exist"
                    self.logger.info(f"Commented out problematic import on line {i+1}")
                    
                    # Write back to file
                    new_content = '\n'.join(lines)
                    script_file.write_text(new_content, encoding="utf-8")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error fixing standard library import: {e}")
            return False
        
    def _move_function_to_top(self, function_name: str, script_path: str) -> bool:
        """Move a function definition to the top of the file to resolve forward references"""
        try:
            content = self._read_file_content(script_path)
            lines = content.split('\n')
            
            # Create backup before modifying
            self._backup_file(script_path)
            script_file = Path(script_path)
            
            # Find the function definition and extract it
            function_lines = []
            function_start = None
            function_end = None
            in_function = False
            indent_level = None
            
            for i, line in enumerate(lines):
                if f"def {function_name}(" in line:
                    function_start = i
                    in_function = True
                    indent_level = len(line) - len(line.lstrip())
                    function_lines.append(line)
                elif in_function:
                    # Check if we're still in the function
                    if line.strip() == "":
                        function_lines.append(line)
                    elif len(line) - len(line.lstrip()) > indent_level:
                        function_lines.append(line)
                    else:
                        function_end = i
                        break
                        
            if function_start is None:
                return False
                
            if function_end is None:
                function_end = len(lines)
            
            # Remove the function from its current location
            new_lines = lines[:function_start] + lines[function_end:]
            
            # Find where to insert the function (after imports but before main code)
            insert_position = 0
            for i, line in enumerate(new_lines):
                if line.strip().startswith(('import ', 'from ')) or line.strip().startswith('#') or line.strip() == "":
                    insert_position = i + 1
                else:
                    break
            
            # Insert the function at the appropriate position
            final_lines = (new_lines[:insert_position] + 
                          function_lines + 
                          [""] +  # Add blank line after function
                          new_lines[insert_position:])
            
            # Write back to file
            new_content = '\n'.join(final_lines)
            script_file.write_text(new_content, encoding="utf-8")
            
            self.logger.info(f"Successfully moved function '{function_name}' to resolve forward reference")
            return True
            
        except Exception as e:
            self.logger.error(f"Error moving function {function_name}: {e}")
            return False
    
    def _suggest_library_import(self, function_name: str, module_name: str = None) -> Optional[List[str]]:
        """Suggest library imports for common functions - delegate to handler"""
        
        handler = ImportErrorHandler()
        return handler.suggest_library_import(function_name, module_name)
