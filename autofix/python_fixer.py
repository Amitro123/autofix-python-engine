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
from .utils import ModuleValidation

# Handle both relative and absolute imports
try:
    from .constants import ErrorType
    from .error_parser import ErrorParser, ParsedError
    from .logging_utils import get_logger
    from .import_suggestions import (
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
            
        # Import suggestions from external configuration
        self.import_suggestions = IMPORT_SUGGESTIONS
        self.stdlib_modules = STDLIB_MODULES
        self.multi_import_suggestions = MULTI_IMPORT_SUGGESTIONS
        self.common_imports = self.import_suggestions
        self.known_pip_packages = KNOWN_PIP_PACKAGES
        self.math_functions = MATH_FUNCTIONS
    
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
        else:
            return [f"Attempt to fix {error.error_type}"]
    
    def _suggest_module_fixes(self, module: str) -> list:
        """Generate suggestions for ModuleNotFoundError"""
        if not module:
            return []
        
        if module in self.known_pip_packages:
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
        elif error_type == ErrorType.SYNTAX_ERROR:
            return self._fix_syntax_error(error)
        elif error_type == ErrorType.INDEX_ERROR:
            return self._fix_index_error(error)
        else:
            self.logger.warning(f"No fix implementation for {error_type.to_string()}")
            return False

    def maybe_install_package(self, package_name: str) -> bool:
        """Install package only if auto_install is enabled"""
        if not self.auto_install:
            self.logger.info(f" Auto install disabled; skipping installation of {package_name}")
            self.logger.info(f" Suggestion: Run with --auto-install flag to enable automatic installation")
            return False
        
        self.logger.info(f" Auto install enabled; installing {package_name}")
        return self.install_package(package_name)

    def _fix_module_not_found_error(self, error: ParsedError) -> bool:
        """Fix ModuleNotFoundError by installing missing packages or creating modules"""
        missing_module = error.missing_module
        if not missing_module:
            return False
        
        self.logger.info(f"Attempting to fix missing module: {missing_module}")
        
        # Check if it's a known pip package
        if missing_module in self.known_pip_packages:
            self.logger.info(f"Installing pip package: {missing_module}")
            return self.maybe_install_package(missing_module)
        
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
        
        # Try to create a local module file
        return self._create_module_file(missing_module, error.file_path)
    
    def _fix_import_error(self, error: ParsedError) -> bool:
        """Fix ImportError by adding missing imports or creating missing __init__.py files"""
        if error.missing_function and error.missing_module:
            # Check if we're trying to import from a standard library module
            if self._is_standard_library_module(error.missing_module):
                self.logger.warning(f"Cannot import '{error.missing_function}' from standard library module '{error.missing_module}' - symbol does not exist")
                return self._fix_standard_library_import_error(error)
            
            # Check if this is a missing __init__.py issue first
            if self._fix_missing_init_files(error.missing_module):
                return True
            
            # Handle "cannot import name 'X' from 'Y'" errors
            import_statement = f"from {error.missing_module} import {error.missing_function}"
            return self._add_import_to_script(import_statement, error.file_path)
        elif error.missing_module:
            # Handle general module import errors
            if self._is_known_pip_package(error.missing_module):
                return self.maybe_install_package(error.missing_module)
        
        return False
    
    def _fix_name_error(self, error: ParsedError) -> bool:
        """Fix NameError by creating missing functions or adding imports"""
        missing_function = error.missing_function
        if not missing_function:
            return False
        
        self.logger.info(f"Attempting to fix undefined name: {missing_function}")
        
        # Check if it's a common function that needs import
        if missing_function in self.common_imports:
            import_statement = self.common_imports[missing_function]
            return self._add_import_to_script(import_statement, error.file_path)
        
        # Check if it's a math function
        if missing_function in self.math_functions:
            import_statement = f"from math import {missing_function}"
            return self._add_import_to_script(import_statement, error.file_path)
        
        # Try to create the function in the script
        return self._create_function_in_script(missing_function, error.file_path)
    
    def _fix_attribute_error(self, error: ParsedError) -> bool:
        """Fix AttributeError by suggesting imports or method creation"""
        if error.missing_attribute and error.missing_module:
            self.logger.info(f"Missing attribute '{error.missing_attribute}' on '{error.missing_module}'")
            # Check if it's a common library function that needs import
            suggestion = self._suggest_library_import(
                error.missing_attribute, error.missing_module)
            if suggestion:
                return self._add_import_to_script(suggestion, error.file_path)
        
        return False

        
    def _fix_index_error(self, error: ParsedError) -> bool:
        """Fix IndexError by adding bounds checking or safe indexing"""
        self.logger.info(f"Attempting to fix IndexError: {error.error_message}")
        
        try:
            lines = self._read_file_lines(error.file_path)
            line_idx = self._validate_line_number(error.line_number, lines)
            if line_idx is None:
                return False
            
            problematic_line = lines[line_idx].strip()
            self.logger.info(f"Problematic line: {problematic_line}")
            
            fixes_applied = self._apply_index_fixes(lines, line_idx, problematic_line, error.error_message)
            
            if fixes_applied:
                return self._save_fixed_file(error.file_path, lines, fixes_applied)
            else:
                self._log_index_error_suggestions()
                return False
                
        except Exception as e:
            self.logger.error(f"Error fixing IndexError: {e}")
            return False
    
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
    
    def _apply_index_fixes(self, lines: list, line_idx: int, problematic_line: str, error_message: str) -> list:
        """Apply index error fixes and return list of applied fixes"""
        import re
        fixes_applied = []
        pattern = r'(\w+)\[(\w+|\d+)\]'
        matches = re.findall(pattern, problematic_line)
        
        if not matches:
            return fixes_applied
        
        original_line = lines[line_idx]
        fixed_line = original_line
        
        # Determine if this is string indexing
        is_string_error = 'str' in error_message.lower() or 'string' in error_message.lower()
        default_value = "''" if is_string_error else "None"
        
        for list_name, index_expr in matches:
            unsafe_access = f"{list_name}[{index_expr}]"
            safe_access = self._create_safe_access(list_name, index_expr, default_value)
            
            fixed_line = fixed_line.replace(unsafe_access, safe_access)
            fixes_applied.append(f"Added bounds check for {list_name}[{index_expr}]")
        
        if fixed_line != original_line:
            lines[line_idx] = fixed_line
            self.logger.info(f"Fixed line: {fixed_line.strip()}")
        
        return fixes_applied
    
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
    
    def _log_index_error_suggestions(self):
        """Log suggestions for manual IndexError fixes"""
        suggestions = [
            "Check list/string length before accessing: if len(my_list) > index:",
            "Use try-except: try: value = my_list[index] except IndexError: value = None",
            "Use get() method for dictionaries or safe indexing"
        ]
        
        self.logger.info("IndexError fix suggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            self.logger.info(f"{i}. {suggestion}")
    
    def _is_known_pip_package(self, module_name: str) -> bool:
        """Check if module is a known pip package"""
        package_name = MODULE_TO_PACKAGE.get(module_name, module_name)
        return package_name in self.known_pip_packages
    
    
    def _create_missing_file(self, module_name: str, script_path: str) -> bool:
        """Create a missing local Python file"""
        try:
            script_dir = Path(script_path).parent
            module_file = script_dir / f"{module_name}.py"
            
            if module_file.exists():
                self.logger.info(f"Module file already exists: {module_file}")
                return False
            
            # Check if we have write permissions
            if not os.access(script_dir, os.W_OK):
                self.logger.error(f"No write permission for directory: {script_dir}")
                return False
            
            self.logger.info(f"Creating missing module file: {module_file}")
            
            module_content = f'''"""
Auto-generated module by AutoFix
Contains placeholder implementations for missing functionality
"""

def placeholder_function():
    """Auto-generated placeholder function"""
    return None
'''
            
            module_file.write_text(module_content, encoding="utf-8")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating module file {module_name}: {e}")
            return False
    
    def _backup_file(self, file_path: str) -> str:
        """Create backup before modifying file"""
        backup_path = f"{file_path}.autofix.bak"
        import shutil
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    def _add_import_to_script(self, import_statement: str, script_path: str) -> bool:
        """Add an import statement to the script"""
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would add import: {import_statement}")
            return True
        try:
            script_file = Path(script_path)
            
            if not script_file.exists():
                self.logger.error(f"Script file not found: {script_path}")
                return False
            
            # Check if we have write permissions
            if not os.access(script_file, os.W_OK):
                self.logger.error(f"No write permission for file: {script_file}")
                return False
            
            # Create backup before modifying
            self._backup_file(script_path)
            
            self.logger.info(f"Adding import: {import_statement}")
            
            content = self._read_file_content(script_path)
            
            # Check if import already exists
            if import_statement in content:
                self.logger.info("Import already exists in file")
                return True
            
            lines = content.split("\n")
            
            # Find the right place to insert the import (after existing imports)
            insert_index = 0
            for i, line in enumerate(lines):
                if line.strip().startswith(("import ", "from ")) or line.strip().startswith("#"):
                    insert_index = i + 1
                elif line.strip() == "":
                    continue
                else:
                    break
            
            # Insert the import statement
            lines.insert(insert_index, import_statement)
            
            new_content = "\n".join(lines)
            script_file.write_text(new_content, encoding="utf-8")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding import to script: {e}")
            return False
    
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
    
    def install_package(self, package_name: str) -> bool:
        """
        Unified pip package installer with improved timeout, mapping, and verification
        
        Args:
            package_name: Name of the module/package to install
        
        Returns:
            bool: True if installation and verification successful, False otherwise
        """
        try:
            self.logger.info(f"Installing package: {package_name}")

            install_name = MODULE_TO_PACKAGE.get(package_name, package_name)
            if install_name != package_name:
                self.logger.info(f"Mapping {package_name} -> {install_name}")

            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", install_name],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes
            )

            if result.returncode == 0:
                self.logger.info(f"Successfully installed {install_name}")

                try:
                    __import__(package_name)
                    self.logger.info(f" Module '{package_name}' verified after installation")
                    return True
                except ImportError as import_err:
                    self.logger.warning(f" Package {install_name} installed but module {package_name} import failed: {import_err}")
                    return False
            else:
                self.logger.error(f"Failed to install {install_name}: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout (5 minutes) while installing {package_name}")
            return False
        except Exception as e:
            self.logger.error(f"Error installing {package_name}: {e}")
            return False

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
    
    def _is_standard_library_module(self, module_name: str) -> bool:
        """Check if a module is part of Python's standard library"""
        # Get the base module name (e.g., 'os' from 'os.path')
        base_module = module_name.split('.')[0]
        return base_module in self.stdlib_modules
    
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
    
    def _create_module_file(self, module_name: str, script_path: str) -> bool:
        """Create a missing module file with basic structure"""
        try:
            # Handle nested module paths like utils.database.connection
            parts = module_name.split('.')
            current_path = Path(script_path).parent
            
            # Create directory structure
            for part in parts[:-1]:
                current_path = current_path / part
                current_path.mkdir(exist_ok=True)
                
                # Create __init__.py if it doesn't exist
                init_file = current_path / "__init__.py"
                if not init_file.exists():
                    init_file.write_text("# Auto-generated __init__.py by AutoFix\n", encoding="utf-8")
            
            # Create the final module file
            module_file = current_path / f"{parts[-1]}.py"
            if not module_file.exists():
                self.logger.info(f"Creating missing module file: {module_file}")
                
                module_content = f'''"""
Auto-generated module by AutoFix
Contains placeholder implementations for missing functionality
"""

def placeholder_function():
    """Auto-generated placeholder function"""
    return "Module {module_name} created by AutoFix"
'''
                module_file.write_text(module_content, encoding="utf-8")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error creating module file {module_name}: {e}")
            return False
    
    def _fix_missing_init_files(self, module_path: str) -> bool:
        """Create missing __init__.py files for package imports"""
        try:
            # Convert module path to directory structure
            parts = module_path.split('.')
            current_path = Path(".")
            
            # Check each level of the package hierarchy
            for part in parts:
                current_path = current_path / part
                if current_path.exists() and current_path.is_dir():
                    init_file = current_path / "__init__.py"
                    if not init_file.exists():
                        self.logger.info(f"Creating missing __init__.py in {current_path}")
                        init_file.write_text("# Auto-generated __init__.py by AutoFix\n", encoding="utf-8")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating __init__.py files: {e}")
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
        """Suggest library imports for common functions"""
        from typing import List
        
        if function_name in self.import_suggestions:
            return [self.import_suggestions[function_name]]
        
        if function_name in self.multi_import_suggestions:
            return self.multi_import_suggestions[function_name]
        
        if function_name in self.math_functions:
            return [f"from math import {function_name}"]
        
        # Check for common patterns
        if function_name.startswith("is") and function_name.endswith("file"):
            return ["from os.path import isfile"]
        
        if function_name.startswith("is") and function_name.endswith("dir"):
            return ["from os.path import isdir"]
        
        return None
    
    def _clear_module_cache(self, script_path: str):
        """Clear only locally created modules"""
        script_dir = Path(script_path).parent
        modules_to_remove = []
        
        for module_name in list(sys.modules.keys()):
            module = sys.modules[module_name]
            if hasattr(module, '__file__') and module.__file__:
                module_path = Path(module.__file__)
                if script_dir in module_path.parents:
                    modules_to_remove.append(module_name)
        
        for module_name in modules_to_remove:
            if module_name in sys.modules:
                del sys.modules[module_name]