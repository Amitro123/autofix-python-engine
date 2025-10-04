#!/usr/bin/env python3
"""
ImportError Handler - Handle ImportError with smart package resolution
"""

import re
import os
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path


# Handle both relative and absolute imports
try:
    from ..import_suggestions import ( 
        IMPORT_SUGGESTIONS, STDLIB_MODULES, KNOWN_PIP_PACKAGES, 
        MODULE_TO_PACKAGE, MULTI_IMPORT_SUGGESTIONS, MATH_FUNCTIONS
    )
    from ..logging_utils import get_logger  # ← .. במקום ...
except ImportError:
    from autofix.import_suggestions import ( 
        IMPORT_SUGGESTIONS, STDLIB_MODULES, KNOWN_PIP_PACKAGES, 
        MODULE_TO_PACKAGE, MULTI_IMPORT_SUGGESTIONS, MATH_FUNCTIONS
    )
    from autofix.logging_utils import get_logger



class ImportErrorHandler:
    """Handle ImportError - missing imports and package resolution"""
    
    def __init__(self):
        self.logger = get_logger("import_error_handler")
    
    def analyze_error(self, error_message: str, file_path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Analyze ImportError
        
        Args:
            error_message: The error message from the exception
            file_path: Path to the file with the error
            
        Returns:
            (can_fix, suggestion, details)
        """
        # Extract module name from various ImportError patterns
        missing_module = self._extract_module_name(error_message)
        
        if not missing_module:
            return False, "Could not determine missing module", {}
        
        details = {
            'missing_module': missing_module,
            'error_message': error_message,
            'file_path': file_path
        }
        
        # Check if it's a known package
        if missing_module in self.known_pip_packages:
            package_name = self.module_to_package.get(missing_module, missing_module)
            suggestion = f"Install package: pip install {package_name}"
            return True, suggestion, details
        
        # Check if it's stdlib (shouldn't fail, but might be version issue)
        base_module = missing_module.split('.')[0]
        if base_module in self.stdlib_modules:
            suggestion = f"Module '{missing_module}' is a standard library module - check Python version"
            return False, suggestion, details
        
        # Relative import error
        if "attempted relative import" in error_message.lower():
            suggestion = "Relative imports require proper package structure"
            return False, suggestion, details
        
        # Suggest creating local module
        suggestion = f"Create local module: {missing_module}.py"
        return True, suggestion, details
    
    def _extract_module_name(self, error_message: str) -> Optional[str]:
        """Extract module name from ImportError message"""
        # Pattern: "No module named 'module_name'"
        match = re.search(r"No module named ['\"]([^'\"]+)['\"]", error_message)
        if match:
            return match.group(1)
        
        # Pattern: "cannot import name 'function' from 'module'"
        match = re.search(r"cannot import name ['\"]([^'\"]+)['\"] from ['\"]([^'\"]+)['\"]", error_message)
        if match:
            return match.group(2)  # Return the module name
        
        return None
    
    def apply_fix(self, error_type: str, file_path: str, details: Dict[str, Any]) -> bool:
        """
        Apply fix for ImportError - now with auto-import!

        Args:
            error_type: Type of error (should be "ImportError")
            file_path: Path to the file with the error
            details: Dictionary containing error details

        Returns:
            bool: True if import was added, False if manual intervention required
        """
        missing_module = details.get('missing_module')
        error_message = details.get('error_message', '')

        if not missing_module:
            print("\nImportError detected but could not determine missing module")
            return False

        print(f"\nImportError detected in {file_path}")
        print(f"Missing module: '{missing_module}'")

        # Check if it's a relative import issue
        if "attempted relative import" in error_message.lower():
            print("\nRelative import error - cannot auto-fix")
            print("Suggestions:")
            print("  1. Use absolute imports instead")
            print("  2. Ensure proper package structure with __init__.py")
            print("  3. Run as module: python -m package.module")
            print("\nImportError requires manual intervention - PARTIAL result")
            return False

        # Try to add the import automatically
        if missing_module in self.import_suggestions:
            import_statement = self.import_suggestions[missing_module]
            self.logger.info(f"Found import suggestion for '{missing_module}': {import_statement}")
            
            if self.add_import_to_script(import_statement, file_path):
                print(f"\n✅ Successfully added import: {import_statement}")
                return True
            else:
                print(f"\n❌ Failed to add import automatically")
                return False

        # Manual suggestions if no auto-fix available
        print("\nCould not auto-fix - manual suggestions:")

        if missing_module in self.known_pip_packages:
            package_name = self.module_to_package.get(missing_module, missing_module)
            print(f"  1. Install package: pip install {package_name}")
        else:
            print(f"  1. Install package: pip install {missing_module}")

        print(f"  2. Create local module: {missing_module}.py")
        print(f"  3. Check import statement spelling")
        print(f"  4. Verify package name and availability")

        print("\nImportError requires manual installation - PARTIAL result")
        return False

    
    def suggest_library_import(self, function_name: str, module_name: str = None) -> Optional[List[str]]:
        """
        Suggest library imports for common functions
        
        Args:
            function_name: Name of the function to import
            module_name: Optional module name context
            
        Returns:
            List of import suggestions or None
        """
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
