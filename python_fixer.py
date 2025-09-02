#!/usr/bin/env python3
"""
Python Fixer - Core Python error fixing logic

Handles automatic fixing of common Python errors including:
- ModuleNotFoundError (pip install, local file creation)
- ImportError (missing imports, function imports)
- NameError (undefined functions, variables)
- AttributeError (missing attributes, methods)
- SyntaxError (version compatibility issues)
"""

import ast
import importlib
import os
import re
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .error_parser import ErrorParser, ParsedError
from .logging_utils import get_logger


class PythonFixer:
    """Core Python error fixing functionality"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.auto_install = self.config.get('auto_install', True)
        self.create_files = self.config.get('create_files', True)
        self.max_recursion_depth = self.config.get('max_retries', 3)
        self.error_parser = ErrorParser()
        self.logger = get_logger("python_fixer")
        self.dry_run = dry_run
            
        # Simple import suggestions (one option per function)
        self.import_suggestions = {
            "sleep": "from time import sleep",
            "time": "import time",
            "datetime": "from datetime import datetime",
            "timedelta": "from datetime import timedelta",
            "date": "from datetime import date",
            "json": "import json",
            "os": "import os",
            "sys": "import sys",
            "random": "import random",
            "math": "import math",
            "DataFrame": "import pandas as pd",
            "array": "import numpy as np",
            "plt": "import matplotlib.pyplot as plt",
            
            # Collections
            "defaultdict": "from collections import defaultdict",
            "Counter": "from collections import Counter",
            "OrderedDict": "from collections import OrderedDict",
            "namedtuple": "from collections import namedtuple",
            "deque": "from collections import deque",
            
            # File system and paths
            "Path": "from pathlib import Path",
            "glob": "import glob",
            "shutil": "import shutil",
            "tempfile": "import tempfile",
            
            # System and process
            "subprocess": "import subprocess",
            "platform": "import platform",
            
            # Concurrency
            "threading": "import threading",
            "multiprocessing": "import multiprocessing",
            "asyncio": "import asyncio",
            
            # Data serialization
            "pickle": "import pickle",
            "csv": "import csv",
            "xml": "import xml",
            
            # Database
            "sqlite3": "import sqlite3",
            
            # Network and web
            "urllib": "import urllib",
            "http": "import http",
            "socket": "import socket",
            
            # Cryptography and encoding
            "hashlib": "import hashlib",
            "base64": "import base64",
            "uuid": "import uuid",
            "secrets": "import secrets",
            
            # Utilities
            "logging": "import logging",
            "argparse": "import argparse",
            "configparser": "import configparser",
            "itertools": "import itertools",
            "functools": "import functools",
            "operator": "import operator",
            "warnings": "import warnings",
            "traceback": "import traceback",
            "copy": "import copy",
            "re": "import re",
            "string": "import string",
            
            # Math and statistics
            "math": "import math",
            "statistics": "import statistics",
            "decimal": "import decimal",
            "fractions": "import fractions",
        }
        
        # Multiple import suggestions for ambiguous functions
        self.multi_import_suggestions = {
            "dump": [
                "import json  # for json.dump",
                "import pickle  # for pickle.dump",
            ],
            "load": [
                "import json  # for json.load",
                "import pickle  # for pickle.load",
            ],
            "dumps": [
                "import json  # for json.dumps",
                "import pickle  # for pickle.dumps",
            ],
            "loads": [
                "import json  # for json.loads",
                "import pickle  # for pickle.loads",
            ],
        }
        
        # Common function imports (alias for backward compatibility)
        self.common_imports = self.import_suggestions
        
        # Known pip packages for common modules
        self.known_pip_packages = {
            "requests", "numpy", "pandas", "matplotlib", "scipy", "sklearn",
            "tensorflow", "torch", "flask", "django", "fastapi", "sqlalchemy",
            "psycopg2", "pymongo", "redis", "celery", "pytest", "black",
            "flake8", "mypy", "pydantic", "click", "typer", "rich", "tqdm",
            "pillow", "opencv-python", "beautifulsoup4", "lxml", "selenium",
            "openpyxl", "xlsxwriter", "python-dateutil", "pytz", "arrow",
            "cryptography", "bcrypt", "jwt", "passlib", "httpx", "aiohttp",
            "uvicorn", "gunicorn", "streamlit", "dash", "plotly", "seaborn",
            "statsmodels", "networkx", "sympy", "nltk", "spacy", "transformers"
        }
        
        # Math functions that need special import
        self.math_functions = {
            "sqrt", "sin", "cos", "tan", "log", "exp", "pow", "ceil", "floor", "abs"
        }
    
    def analyze_potential_fixes(self, script_path: str) -> None:
        """
        Analyze a script and identify potential fixes without making changes
        
        Args:
            script_path: Path to the Python script to analyze
        """
        try:
            self.logger.info(f"Analyzing script for potential fixes: {script_path}")
            
            # Try to run the script to capture errors
            import runpy
            runpy.run_path(script_path, run_name="__main__")
            self.logger.info("Script runs without errors - no fixes needed")
            
        except Exception as e:
            self.logger.info(f"Found error that would be fixed: {type(e).__name__}: {e}")
            
            # Parse the error to show what fix would be applied
            parsed_error = self.error_parser.parse_exception(e, script_path)
            
            if parsed_error.error_type == "ModuleNotFoundError":
                if parsed_error.missing_module in self.known_pip_packages:
                    self.logger.info(f"Would install pip package: {parsed_error.missing_module}")
                else:
                    package_name = self._resolve_package_name(parsed_error.missing_module)
                    if package_name and package_name != parsed_error.missing_module:
                        self.logger.info(f"Would install pip package: {package_name} (for module {parsed_error.missing_module})")
                    else:
                        self.logger.info(f"Would create local module file: {parsed_error.missing_module}.py")
            
            elif parsed_error.error_type == "NameError":
                if parsed_error.missing_function in self.common_imports:
                    import_stmt = self.common_imports[parsed_error.missing_function]
                    self.logger.info(f"Would add import: {import_stmt}")
                elif parsed_error.missing_function in self.math_functions:
                    self.logger.info(f"Would add import: from math import {parsed_error.missing_function}")
                else:
                    self.logger.info(f"Would create function: {parsed_error.missing_function}()")
            
            elif parsed_error.error_type == "ImportError":
                if parsed_error.missing_function and parsed_error.missing_module:
                    self.logger.info(f"Would add import: from {parsed_error.missing_module} import {parsed_error.missing_function}")
            
            elif parsed_error.error_type == "SyntaxError":
                self.logger.info(f"Would attempt to fix syntax error: {parsed_error.error_message}")
            
            else:
                self.logger.info(f"Would attempt to fix {parsed_error.error_type}")

    def run_script_with_fixes(self, script_path: str, recursion_depth: int = 0) -> bool:
        """
        Run Python script with automatic error fixing
        
        Args:
            script_path: Path to the Python script to execute
            recursion_depth: Current recursion depth to prevent infinite loops
            
        Returns:
            bool: True if script executed successfully, False otherwise
        """
        if recursion_depth > self.max_recursion_depth:
            self.logger.error(
                f"Maximum recursion depth ({self.max_recursion_depth}) reached. "
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
            if self.fix_error(parsed_error):
                self.logger.info("Error fixed, retrying script execution...")
                self._clear_module_cache(script_path)
                return self.run_script_with_fixes(script_path, recursion_depth + 1)
            else:
                self.logger.error(f"Could not auto-resolve {parsed_error.error_type}")
                return False
        finally:
            os.chdir(original_cwd)
    
    def fix_error(self, error: ParsedError) -> bool:
        """
        Fix a parsed error based on its type
        
        Args:
            error: Parsed error information
            
        Returns:
            bool: True if error was fixed, False otherwise
        """
        if error.error_type == "ModuleNotFoundError":
            return self._fix_module_not_found_error(error)
        elif error.error_type == "ImportError":
            return self._fix_import_error(error)
        elif error.error_type == "NameError":
            return self._fix_name_error(error)
        elif error.error_type == "AttributeError":
            return self._fix_attribute_error(error)
        elif error.error_type == "SyntaxError":
            return self._fix_syntax_error(error)
        else:
            self.logger.warning(f"No fix available for {error.error_type}")
            return False
    
    def _fix_module_not_found_error(self, error: ParsedError) -> bool:
        """Fix ModuleNotFoundError by installing missing packages or creating modules"""
        missing_module = error.missing_module
        if not missing_module:
            return False
        
        self.logger.info(f"Attempting to fix missing module: {missing_module}")
        
        # Check if it's a known pip package
        if missing_module in self.known_pip_packages:
            self.logger.info(f"Installing pip package: {missing_module}")
            return self._install_pip_package(missing_module)
        
        # Check for common package name variations
        package_name = self._resolve_package_name(missing_module)
        if package_name and package_name != missing_module:
            self.logger.info(f"Installing pip package: {package_name} (for module {missing_module})")
            return self._install_pip_package(package_name)
        
        # Check if this looks like a real module name or just a test
        if self._is_likely_test_module(missing_module):
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
                # Try to suggest alternative imports or remove the problematic import
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
                return self._install_package(error.missing_module)
        
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
            self.logger.info(
                f"Missing attribute '{error.missing_attribute}' on '{error.missing_module}'"
            )
            
            # Check if it's a common library function that needs import
            suggestion = self._suggest_library_import(
                error.missing_attribute, error.missing_module
            )
            if suggestion:
                return self._add_import_to_script(suggestion, error.file_path)
        
        return False
    
    def _fix_syntax_error(self, error: ParsedError) -> bool:
        """Fix SyntaxError by applying common fixes and formatting"""
        self.logger.info(f"Attempting to fix SyntaxError: {error.error_message}")
        
        # Try to fix common syntax issues
        if self._fix_common_syntax_issues(error.file_path, error.error_message):
            return True
        
        # Try to format the file with basic fixes
        if self._apply_basic_formatting(error.file_path):
            return True
            
        # Provide guidance for version compatibility issues
        if error.syntax_details and "version_issue" in error.syntax_details:
            version_issue = error.syntax_details["version_issue"]
            self.logger.warning(
                f"Version compatibility issue: {version_issue['feature']} "
                f"requires Python {version_issue['required_version']}, "
                f"but you have {version_issue['current_version']}"
            )
            self.logger.info(f"Suggestion: {version_issue['suggestion']}")
        
        # For now, we can't automatically fix syntax errors
        # but we provide helpful information
        return False
    
    def _is_known_pip_package(self, module_name: str) -> bool:
        """Check if module is a known pip package"""
        # Handle module aliases (e.g., cv2 -> opencv-python)
        module_aliases = {
            "cv2": "opencv-python",
            "PIL": "pillow",
            "bs4": "beautifulsoup4",
            "yaml": "pyyaml",
            "dateutil": "python-dateutil"
        }
        
        package_name = module_aliases.get(module_name, module_name)
        return package_name in self.known_pip_packages
    
    def _install_package(self, package_name: str) -> bool:
        """Install a package using pip"""
        try:
            self.logger.info(f"Installing package: {package_name}")
            
            # Handle module aliases for installation
            install_aliases = {
                "cv2": "opencv-python",
                "PIL": "pillow",
                "bs4": "beautifulsoup4",
                "yaml": "pyyaml",
                "dateutil": "python-dateutil"
            }
            
            install_name = install_aliases.get(package_name, package_name)
            
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", install_name],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                self.logger.info(f"Successfully installed {install_name}")
                return True
            else:
                self.logger.error(f"Failed to install {install_name}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout while installing {package_name}")
            return False
        except Exception as e:
            self.logger.error(f"Error installing {package_name}: {e}")
            return False
    
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
            backup_path = self._backup_file(script_path)
            
            self.logger.info(f"Adding import: {import_statement}")
            
            content = script_file.read_text(encoding="utf-8")
            
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
            script_file = Path(script_path)
            
            if not script_file.exists():
                return False
            
            # Check if we have write permissions
            if not os.access(script_file, os.W_OK):
                self.logger.error(f"No write permission for file: {script_file}")
                return False
            
            # Create backup before modifying
            backup_path = self._backup_file(script_path)
            
            content = script_file.read_text(encoding="utf-8")
            
            # Check if function already exists and handle forward references
            if f"def {function_name}(" in content:
                self.logger.info(f"Function '{function_name}' already exists in {script_file.name}")
                # Check if it's a forward reference issue - function defined after usage
                lines = content.split('\n')
                function_def_line = None
                first_usage_line = None
                
                for i, line in enumerate(lines):
                    if f"def {function_name}(" in line and function_def_line is None:
                        function_def_line = i
                    if function_name in line and "def " not in line and first_usage_line is None:
                        first_usage_line = i
                
                # If function is defined after first usage, move it to the top
                if function_def_line is not None and first_usage_line is not None and function_def_line > first_usage_line:
                    self.logger.info(f"Moving function '{function_name}' to resolve forward reference")
                    return self._move_function_to_top(function_name, script_path)
                
                return False
            
            # Analyze function usage to determine parameters
            params = self._analyze_function_usage(function_name, content)
            param_str = ", ".join(params) if params else ""
            
            # Create function with intelligent parameter detection
            if len(params) == 2:
                impl = f"return {params[0]} + {params[1]} if {params[0]} and {params[1]} else 0  # Basic calculation"
            elif len(params) == 1:
                impl = f"return len({params[0]}) if hasattr({params[0]}, '__len__') else {params[0]}"
            else:
                impl = "return 42  # Default return value"
            
            function_code = f"""

def {function_name}({param_str}):
    \"\"\"Auto-generated function by AutoFix
    
    Parameters detected from usage analysis.
    TODO: Add proper implementation
    \"\"\"
    # Placeholder implementation based on usage context
    {impl}
"""
            
            self.logger.info(f"Created missing function: {function_name}")
            
            # Append the function to the file
            new_content = content.rstrip() + function_code
            script_file.write_text(new_content, encoding="utf-8")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating function {function_name}: {e}")
            return False
    
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
    
    def _install_pip_package(self, package_name: str) -> bool:
        """Install a pip package using subprocess"""
        try:
            import subprocess
            import sys
            
            self.logger.info(f"Installing package: {package_name}")
            
            # Run pip install command
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package_name],
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            if result.returncode == 0:
                self.logger.info(f"Successfully installed {package_name}")
                return True
            else:
                self.logger.error(f"Failed to install {package_name}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout while installing {package_name}")
            return False
        except Exception as e:
            self.logger.error(f"Error installing {package_name}: {e}")
            return False
    
    def _resolve_package_name(self, module_name: str) -> Optional[str]:
        """Resolve module name to actual pip package name"""
        # Common module name to package name mappings
        module_to_package = {
            "cv2": "opencv-python",
            "PIL": "Pillow",
            "sklearn": "scikit-learn",
            "yaml": "PyYAML",
            "dateutil": "python-dateutil",
            "jwt": "PyJWT",
            "bs4": "beautifulsoup4",
            "psycopg2": "psycopg2-binary",
            "MySQLdb": "mysqlclient",
            "Image": "Pillow",
            "requests_oauthlib": "requests-oauthlib",
            "google.cloud": "google-cloud",
            "tensorflow": "tensorflow",
            "torch": "torch",
            "torchvision": "torchvision",
            "transformers": "transformers",
            "huggingface_hub": "huggingface-hub",
        }
        
        return module_to_package.get(module_name)
    
    def _fix_common_syntax_issues(self, file_path: str, error_message: str) -> bool:
        """Fix common syntax issues like missing colons, parentheses, etc."""
        try:
            script_file = Path(file_path)
            content = script_file.read_text(encoding="utf-8")
            lines = content.split('\n')
            modified = False
            
            # Create backup before modifying
            backup_path = self._backup_file(file_path)
            
            # Fix missing colons after if/for/while/def/class statements
            if "expected ':'" in error_message.lower() or ("invalid syntax" in error_message.lower() and ":" in error_message):
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if (stripped.startswith(('if ', 'for ', 'while ', 'def ', 'class ', 'elif ', 'else', 'try', 'except', 'finally')) 
                        and not stripped.endswith(':') and not stripped.endswith('\\')
                        and '#' not in stripped):
                        lines[i] = line + ':'
                        modified = True
                        self.logger.info(f"Added missing colon to line {i+1}: {stripped}")
            
            # Fix missing parentheses in print statements (Python 2 to 3)
            if "print" in error_message.lower():
                for i, line in enumerate(lines):
                    if 'print ' in line and not line.strip().startswith('#'):
                        # Simple print statement fix
                        if not ('print(' in line):
                            lines[i] = line.replace('print ', 'print(') + ')'
                            modified = True
                            self.logger.info(f"Fixed print statement on line {i+1}")
            
            if modified:
                new_content = '\n'.join(lines)
                script_file.write_text(new_content, encoding="utf-8")
                return True
                
        except Exception as e:
            self.logger.error(f"Error fixing syntax issues: {e}")
            
        return False
    
    def _apply_basic_formatting(self, file_path: str) -> bool:
        """Apply basic formatting fixes to resolve syntax issues"""
        try:
            script_file = Path(file_path)
            content = script_file.read_text(encoding="utf-8")
            
            # Create backup before modifying
            backup_path = self._backup_file(file_path)
            
            # Basic formatting fixes
            lines = content.split('\n')
            formatted_lines = []
            
            for line in lines:
                # Fix common indentation issues
                if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                    # Check if this should be indented (simple heuristic)
                    if any(keyword in line for keyword in ['return ', 'print(', 'pass', '=']):
                        # Look at previous line to see if it needs indentation
                        if formatted_lines and formatted_lines[-1].strip().endswith(':'):
                            line = '    ' + line
                
                formatted_lines.append(line)
            
            # Check if any changes were made
            new_content = '\n'.join(formatted_lines)
            if new_content != content:
                script_file.write_text(new_content, encoding="utf-8")
                self.logger.info("Applied basic formatting fixes")
                return True
                
        except Exception as e:
            self.logger.error(f"Error applying formatting: {e}")
            
        return False
    
    def _is_likely_test_module(self, module_name: str) -> bool:
        """Detect if a module name appears to be a test/placeholder"""
        test_indicators = [
            "non_existent", "nonexistent", "fake", "test", "dummy", 
            "placeholder", "example", "sample", "mock", "invalid"
        ]
        
        module_lower = module_name.lower()
        return any(indicator in module_lower for indicator in test_indicators)
    
    def _is_standard_library_module(self, module_name: str) -> bool:
        """Check if a module is part of Python's standard library"""
        # Get the base module name (e.g., 'os' from 'os.path')
        base_module = module_name.split('.')[0]
        return base_module in self.stdlib_modules
    
    def _fix_standard_library_import_error(self, error: ParsedError) -> bool:
        """Handle import errors from standard library modules by removing problematic imports"""
        try:
            script_file = Path(error.file_path)
            content = script_file.read_text(encoding="utf-8")
            lines = content.split('\n')
            
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
            script_file = Path(script_path)
            content = script_file.read_text(encoding="utf-8")
            lines = content.split('\n')
            
            # Create backup before modifying
            backup_path = self._backup_file(script_path)
            
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