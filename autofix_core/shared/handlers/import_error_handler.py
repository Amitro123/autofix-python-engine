#!/usr/bin/env python3
"""
ImportError Handler - Handle ImportError with smart package resolution
"""

import re
import os
from typing import Dict, Any, Optional, Tuple
from pathlib import Path


# Handle both relative and absolute imports
try:
    from ..import_suggestions import (
        IMPORT_SUGGESTIONS, STDLIB_MODULES, KNOWN_PIP_PACKAGES,
        MODULE_TO_PACKAGE, MULTI_IMPORT_SUGGESTIONS, MATH_FUNCTIONS
    )
    from ..helpers.logging_utils import get_logger  # ← .. במקום ...
    from ..constants import RegexPatterns, BACKUP_EXTENSION
except ImportError:
    from autofix_core.shared.import_suggestions import (
        IMPORT_SUGGESTIONS, STDLIB_MODULES, KNOWN_PIP_PACKAGES,
        MODULE_TO_PACKAGE, MULTI_IMPORT_SUGGESTIONS, MATH_FUNCTIONS
    )
    from autofix_core.shared.helpers.logging_utils import get_logger
    from autofix_core.shared.constants import RegexPatterns, BACKUP_EXTENSION



class ImportErrorHandler:
    """Handle ImportError - missing imports and package resolution"""
    
    def __init__(self, dry_run: bool = False, quiet: bool = False):
        self.logger = get_logger("import_error_handler")
        self.dry_run = dry_run
        self.quiet = quiet
        self.import_suggestions = IMPORT_SUGGESTIONS
        self.stdlib_modules = STDLIB_MODULES
        self.known_pip_packages = KNOWN_PIP_PACKAGES
        self.module_to_package = MODULE_TO_PACKAGE
        self.multi_import_suggestions = MULTI_IMPORT_SUGGESTIONS
        self.math_functions = MATH_FUNCTIONS

    def _print(self, message: str) -> None:
        """Print a human-facing progress message, unless running quiet.

        Callers that share this process's real stdout with something
        else (e.g. an MCP server's stdio JSON-RPC transport) must be able
        to suppress these without touching global state like
        contextlib.redirect_stdout, which is not concurrency-safe: two
        overlapping redirect_stdout windows in different threads can
        restore each other's saved stream on exit, leaking output into
        the wrong place or losing it. quiet=True avoids that entirely by
        never writing to stdout in the first place.
        """
        if not self.quiet:
            print(message)
    
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
        match = re.search(RegexPatterns.MODULE_NAME, error_message)
        if match:
            return match.group(1)

        # Pattern: "cannot import name 'function' from 'module'"
        match = re.search(RegexPatterns.CANNOT_IMPORT_NAME, error_message)
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
            self._print("\nImportError detected but could not determine missing module")
            return False

        self._print(f"\nImportError detected in {file_path}")
        self._print(f"Missing module: '{missing_module}'")

        # Check if it's a relative import issue
        if "attempted relative import" in error_message.lower():
            self._print("\nRelative import error - cannot auto-fix")
            self._print("Suggestions:")
            self._print("  1. Use absolute imports instead")
            self._print("  2. Ensure proper package structure with __init__.py")
            self._print("  3. Run as module: python -m package.module")
            self._print("\nImportError requires manual intervention - PARTIAL result")
            return False

        # Try to add the import automatically
        if missing_module in self.import_suggestions:
            import_statement = self.import_suggestions[missing_module]
            self.logger.info(f"Found import suggestion for '{missing_module}': {import_statement}")

            if self.add_import_to_script(import_statement, file_path):
                self._print(f"\n✅ Successfully added import: {import_statement}")
                return True
            else:
                self._print(f"\n❌ Failed to add import automatically")
                return False

        # Manual suggestions if no auto-fix available
        self._print("\nCould not auto-fix - manual suggestions:")

        if missing_module in self.known_pip_packages:
            package_name = self.module_to_package.get(missing_module, missing_module)
            self._print(f"  1. Install package: pip install {package_name}")
        else:
            self._print(f"  1. Install package: pip install {missing_module}")

        self._print(f"  2. Create local module: {missing_module}.py")
        self._print(f"  3. Check import statement spelling")
        self._print(f"  4. Verify package name and availability")

        self._print("\nImportError requires manual installation - PARTIAL result")
        return False

    def _backup_file(self, file_path: str) -> str:
        """Create backup before modifying file"""
        backup_path = f"{file_path}{BACKUP_EXTENSION}"
        import shutil
        shutil.copy2(file_path, backup_path)
        return backup_path

    def _read_file_content(self, file_path: str) -> str:
        """Read file content with UTF-8 encoding"""
        return Path(file_path).read_text(encoding="utf-8")

    def add_import_to_script(self, import_statement: str, script_path: str) -> bool:
        """Add an import statement to the script.

        Public: this is the reusable "insert an import line into a file"
        primitive, not just an apply_fix implementation detail -- the MCP
        adapter's NameError fix tier (fix_error_adapter.py) calls it
        directly for names that resolve to a confident single import but
        don't go through apply_fix's own missing_module-keyed dispatch.
        """
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
