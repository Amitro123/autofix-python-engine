#!/usr/bin/env python3
"""
ModuleNotFoundError Handler - Complete Unified Module Management
================================================================

This handler provides complete module management functionality:
- Module name validation (test detection, package name resolution)
- Module file creation (simple, nested, with templates)
- Package installation via pip
- ModuleNotFoundError detection and fixing

All module-related logic is centralized here.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

# Handle both relative and absolute imports
try:
    from ..import_suggestions import (
        IMPORT_SUGGESTIONS, STDLIB_MODULES, KNOWN_PIP_PACKAGES,
        MODULE_TO_PACKAGE
    )
    from ..logging_utils import get_logger
    from ..constants import ValidationPatterns
except ImportError:
    from autofix.import_suggestions import (
        IMPORT_SUGGESTIONS, STDLIB_MODULES, KNOWN_PIP_PACKAGES,
        MODULE_TO_PACKAGE
    )
    from autofix.logging_utils import get_logger
    from autofix.constants import ValidationPatterns


# ========================================================================
# SECTION 1: MODULE VALIDATION
# ========================================================================

class ModuleValidation:
    """
    Module name validation utilities
    Checks if modules are test/placeholder names and resolves package names
    """
    
    @staticmethod
    def is_likely_test_module(module_name: str) -> bool:
        """
        Check if module name looks like a test/demo/placeholder
        
        Args:
            module_name: Name of the module to check
            
        Returns:
            True if module appears to be a test/placeholder module
        """
        if not module_name:
            return False
        
        module_lower = module_name.lower()
        
        # Check exact regex patterns first (more precise)
        for pattern in ValidationPatterns.TEST_MODULE_PATTERNS:
            if re.match(pattern, module_lower):
                return True
        
        # Fallback to substring check
        return any(indicator in module_lower
                  for indicator in ValidationPatterns.TEST_MODULE_INDICATORS)
    
    @staticmethod
    def resolve_package_name(module_name: str) -> Optional[str]:
        """
        Resolve module name to actual package name
        Example: 'cv2' -> 'opencv-python'
        
        Args:
            module_name: Module name from import statement
            
        Returns:
            Actual pip package name or None if not found
        """
        return MODULE_TO_PACKAGE.get(module_name)


# ========================================================================
# SECTION 2: MODULE CREATION
# ========================================================================

class ModuleCreator:
    """
    Handles creation of placeholder modules and files
    Supports simple modules, nested modules, and custom templates
    """
    
    def __init__(self, template_config: Optional[Dict[str, Any]] = None):
        self.template_config = template_config or {}
        self.logger = get_logger("module_creator")
    
    def create_module_file(self, module_name: str, script_path: str, 
                          content_template: Optional[str] = None) -> bool:
        """
        Create a module file with customizable content
        
        Args:
            module_name: Name of the module to create
            script_path: Path to the script that imports the module
            content_template: Optional custom template content
            
        Returns:
            True if module created successfully, False otherwise
        """
        try:
            script_dir = Path(script_path).parent
            module_file = script_dir / f"{module_name}.py"
            
            if module_file.exists():
                self.logger.info(f"Module file already exists: {module_file}")
                return True
            
            content = content_template or self._get_default_template(module_name)
            module_file.write_text(content, encoding='utf-8')
            
            self.logger.info(f"Created module file: {module_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create module file {module_name}: {e}")
            return False
    
    def create_nested_module_file(self, module_name: str, script_path: str) -> bool:
        """
        Create nested module structure (e.g., utils.database.connection)
        Creates all necessary directories and __init__.py files
        
        Args:
            module_name: Dot-separated module path (e.g., 'utils.database.connection')
            script_path: Path to the script that imports the module
            
        Returns:
            True if module created successfully, False otherwise
        """
        try:
            parts = module_name.split('.')
            current_path = Path(script_path).parent
            
            # Create directory structure
            for part in parts[:-1]:
                current_path = current_path / part
                current_path.mkdir(exist_ok=True)
                
                # Create __init__.py if it doesn't exist
                init_file = current_path / "__init__.py"
                if not init_file.exists():
                    init_file.write_text("# Auto-generated by AutoFix\n", encoding="utf-8")
                    self.logger.info(f"Created __init__.py: {init_file}")
            
            # Create the final module file
            module_file = current_path / f"{parts[-1]}.py"
            if not module_file.exists():
                module_content = self._get_nested_template(module_name)
                module_file.write_text(module_content, encoding="utf-8")
                self.logger.info(f"Created nested module: {module_file}")
                return True
            
            self.logger.info(f"Nested module already exists: {module_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating nested module {module_name}: {e}")
            return False
    
    def create_function_module(self, module_name: str, script_path: str, 
                             functions: List[str]) -> bool:
        """
        Create a module with placeholder functions
        
        Args:
            module_name: Name of the module to create
            script_path: Path to the script that imports the module
            functions: List of function names to create as placeholders
            
        Returns:
            True if module created successfully
        """
        template = self._get_function_template(module_name, functions)
        return self.create_module_file(module_name, script_path, template)
    
    def _get_default_template(self, module_name: str) -> str:
        """Default module template"""
        return f'''"""
{module_name} - Auto-generated module by AutoFix
"""

__version__ = "0.1.0"

def placeholder_function():
    """Placeholder function - replace with actual implementation"""
    pass
'''
    
    def _get_nested_template(self, module_name: str) -> str:
        """Template for nested modules"""
        return f'''"""
Auto-generated module by AutoFix
Module path: {module_name}
"""

def placeholder_function():
    """Auto-generated placeholder"""
    return "Module {module_name} created by AutoFix"
'''
    
    def _get_function_template(self, module_name: str, functions: List[str]) -> str:
        """Template with specific functions"""
        content = f'''"""
{module_name} - Auto-generated module with functions
"""

'''
        for func in functions:
            content += f'''
def {func}(*args, **kwargs):
    """Placeholder for {func}"""
    pass
'''
        
        return content


# ========================================================================
# SECTION 3: PACKAGE INSTALLATION
# ========================================================================

class PackageInstaller:
    """
    Handles pip package installation with validation and verification
    """
    
    def __init__(self, auto_install: bool = False, timeout: int = 300):
        self.auto_install = auto_install
        self.timeout = timeout  # 5 minutes default
        self.logger = get_logger("package_installer")
    
    def install_package(self, package_name: str, verify: bool = True) -> bool:
        """
        Install a Python package using pip
        
        Args:
            package_name: Name of the package to install
            verify: Whether to verify import after installation
            
        Returns:
            True if installation successful, False otherwise
        """
        if not self.auto_install:
            self.logger.warning(f"Auto-install disabled, skipping {package_name}")
            return False
        
        try:
            # Use module mapping if available
            install_name = MODULE_TO_PACKAGE.get(package_name, package_name)
            if install_name != package_name:
                self.logger.info(f"Mapping {package_name} -> {install_name}")
            
            self.logger.info(f"Installing package: {install_name}")
            
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", install_name],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                self.logger.info(f"Successfully installed {install_name}")
                
                # Verify import works if requested
                if verify:
                    return self.verify_installation(package_name)
                
                return True
            else:
                self.logger.error(f"Failed to install {install_name}: {result.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout ({self.timeout}s) while installing {package_name}")
            return False
        except Exception as e:
            self.logger.error(f"Error installing {package_name}: {e}")
            return False
    
    def verify_installation(self, module_name: str) -> bool:
        """
        Verify that a module can be imported after installation
        
        Args:
            module_name: Name of the module to verify
            
        Returns:
            True if module imports successfully
        """
        try:
            __import__(module_name)
            self.logger.info(f"Module '{module_name}' verified after installation")
            return True
        except ImportError as e:
            self.logger.warning(f"Module '{module_name}' import failed after installation: {e}")
            return False


# ========================================================================
# SECTION 4: MAIN HANDLER
# ========================================================================

class ModuleNotFoundHandler:
    """
    Main handler for ModuleNotFoundError
    Orchestrates validation, installation, and module creation
    """
    
    def __init__(self, auto_install: bool = False, create_files: bool = True):
        self.validation = ModuleValidation()
        self.creator = ModuleCreator()
        self.installer = PackageInstaller(auto_install=auto_install)
        self.logger = get_logger("module_not_found_handler")
        
        self.stdlib_modules = STDLIB_MODULES
        self.known_pip_packages = KNOWN_PIP_PACKAGES
        self.auto_install = auto_install
        self.create_files = create_files
    
    def analyze_error(self, error_message: str, file_path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Analyze ModuleNotFoundError
        
        Args:
            error_message: The error message from the exception
            file_path: Path to the file with the error
            
        Returns:
            (can_fix, suggestion, details)
        """
        # Extract module name
        missing_module = self._extract_module_name(error_message)
        
        if not missing_module:
            return False, "Could not determine missing module", {}
        
        details = {
            'missing_module': missing_module,
            'error_message': error_message,
            'file_path': file_path,
            'is_test_module': self.validation.is_likely_test_module(missing_module)
        }
        
        # Check if it's a test/demo module
        if details['is_test_module']:
            suggestion = f"Create placeholder module: {missing_module}.py"
            return True, suggestion, details
        
        # Check if it's a known package
        if missing_module in self.known_pip_packages:
            package_name = self.validation.resolve_package_name(missing_module) or missing_module
            suggestion = f"Install package: pip install {package_name}"
            return True, suggestion, details
        
        # Check if it's stdlib
        base_module = missing_module.split('.')[0]
        if base_module in self.stdlib_modules:
            suggestion = f"Module '{missing_module}' is a standard library module"
            return False, suggestion, details
        
        # Unknown module - suggest creating locally
        suggestion = f"Create local module: {missing_module}.py"
        return True, suggestion, details
    
    def apply_fix(self, error_type: str, file_path: str, details: Dict[str, Any]) -> bool:
        """
        Apply fix for ModuleNotFoundError
        
        Args:
            error_type: Type of error (should be "ModuleNotFoundError")
            file_path: Path to the file with the error
            details: Dictionary containing error details
            
        Returns:
            True if fix applied successfully, False otherwise
        """
        missing_module = details.get('missing_module')
        is_test_module = details.get('is_test_module', False)
        
        if not missing_module:
            self.logger.error("Cannot fix: missing_module not provided")
            return False
        
        self.logger.info(f"Attempting to fix ModuleNotFoundError: {missing_module}")
        
        # If it's a test module, create placeholder
        if is_test_module:
            return self._create_module_file(missing_module, file_path)
        
        # If it's a known package, try to install
        if missing_module in self.known_pip_packages:
            return self.installer.install_package(missing_module)
        
        # For unknown modules, create local module file
        return self._create_module_file(missing_module, file_path)
    
    def _extract_module_name(self, error_message: str) -> Optional[str]:
        """Extract module name from ModuleNotFoundError message"""
        # Pattern: "No module named 'module_name'"
        match = re.search(r"No module named ['\"]([^'\"]+)['\"]", error_message)
        if match:
            return match.group(1)
        return None
    
    def _create_module_file(self, module_name: str, script_path: str) -> bool:
        """
        Create a placeholder module file
        
        Args:
            module_name: Name of the module to create
            script_path: Path to the script that imports the module
            
        Returns:
            True if module created successfully, False otherwise
        """
        # Check if file creation is enabled
        if not self.create_files:
            self.logger.info(f"File creation disabled. Module {module_name} not created.")
            return False
        
        # Check if nested module (has dots)
        if '.' in module_name:
            return self.creator.create_nested_module_file(module_name, script_path)
        else:
            return self.creator.create_module_file(module_name, script_path)
