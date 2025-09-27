"""Shared package installation utilities"""
import subprocess
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
import logging

try:
    from .import_suggestions import MODULE_TO_PACKAGE
except ImportError:
    from import_suggestions import MODULE_TO_PACKAGE

logger = logging.getLogger(__name__)

class ModuleCreator:
    """Handles creation of placeholder modules and files"""
    
    def __init__(self, template_config: Optional[Dict[str, Any]] = None):
        self.template_config = template_config or {}
    
    def create_module_file(self, module_name: str, script_path: str, 
                          content_template: Optional[str] = None) -> bool:
        """Create a module file with customizable content"""
        try:
            script_dir = Path(script_path).parent
            module_file = script_dir / f"{module_name}.py"
            
            if module_file.exists():
                logger.info(f"Module file already exists: {module_file}")
                return True
            
            content = content_template or self._get_default_template(module_name)
            module_file.write_text(content, encoding='utf-8')
            
            logger.info(f"Created module file: {module_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create module file {module_name}: {e}")
            return False
    
    def create_local_module(self, module_name: str, script_path: str) -> bool:
        """Create a basic local module file (legacy compatibility)"""
        template = self._get_simple_template(module_name)
        return self.create_module_file(module_name, script_path, template)
    
    def create_function_module(self, module_name: str, script_path: str, 
                             functions: list) -> bool:
        """Create a module with placeholder functions"""
        template = self._get_function_template(module_name, functions)
        return self.create_module_file(module_name, script_path, template)
    
    def _get_default_template(self, module_name: str) -> str:
        """Default module template"""
        return f'''"""
{module_name} - Auto-generated module by AutoFix
"""

# Module version
__version__ = "0.1.0"

def placeholder_function():
    """Placeholder function"""
    pass

# Add your module content here
'''
    
    def _get_simple_template(self, module_name: str) -> str:
        """Simple template for basic modules"""
        return f'''"""
{module_name} - Auto-generated module
"""

# Add your module content here
pass
'''
    
    def _get_function_template(self, module_name: str, functions: list) -> str:
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
    
    def create_init_file(self, directory_path: str) -> bool:
        """Create __init__.py file"""
        try:
            init_file = Path(directory_path) / "__init__.py"
            if not init_file.exists():
                init_file.write_text('"""Package initialization"""\n', encoding='utf-8')
                logger.info(f"Created __init__.py: {init_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to create __init__.py: {e}")
            return False

    def create_nested_module_file(self, module_name: str, script_path: str) -> bool:
        """Create a missing module file with basic structure, handling nested paths"""
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
                logger.info(f"Creating missing module file: {module_file}")
                
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
            logger.error(f"Error creating module file {module_name}: {e}")
            return False


class PackageInstaller:

    def __init__(self, auto_install: bool = False, timeout: int = 300):  # ← 5 minutes
        self.auto_install = auto_install
        self.timeout = timeout
        self.logger = logger
    
    def install_package(self, package_name: str) -> bool:
        """
        Unified pip package installer with improved timeout, mapping, and verification
        """
        if not self.auto_install:
            self.logger.warning(f"Auto-install disabled, skipping {package_name}")
            return False
            
        try:
            self.logger.info(f"Installing package: {package_name}")

            # Use your module mapping
            install_name = MODULE_TO_PACKAGE.get(package_name, package_name)
            if install_name != package_name:
                self.logger.info(f"Mapping {package_name} -> {install_name}")

            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", install_name],
                capture_output=True,
                text=True,
                timeout=self.timeout  # 5 minutes
            )

            if result.returncode == 0:
                self.logger.info(f"Successfully installed {install_name}")

                # Verify import works
                try:
                    __import__(package_name)
                    self.logger.info(f"Module '{package_name}' verified after installation")
                    return True
                except ImportError as import_err:
                    self.logger.warning(f"Package {install_name} installed but module {package_name} import failed: {import_err}")
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
    
    def create_local_module(self, module_name: str, script_path: str) -> bool:

        """Create a basic local module file"""
        try:
            script_dir = Path(script_path).parent
            module_file = script_dir / f"{module_name}.py"
            
            if not module_file.exists():
                content = f'''"""
{module_name} - Auto-generated module
"""

# Add your module content here
pass
'''
                module_file.write_text(content, encoding='utf-8')
                logger.info(f"Created local module: {module_file}")
                return True
            
            return True
        except Exception as e:
            logger.error(f"Failed to create local module {module_name}: {e}")
            return False
    
    def install_or_create_fallback(self, package_name: str, module_name: str, script_path: str) -> bool:
        """Try to install package, create local module as fallback"""
        if self.install_package(package_name):
            return True
        
        logger.info(f"Package installation failed, creating local module for {module_name}")
        return self.create_local_module(module_name, script_path)
