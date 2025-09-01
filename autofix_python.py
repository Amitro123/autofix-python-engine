#!/usr/bin/env python3
"""
AutoFix Python Engine - Pure Python Error Resolution
A lightweight, AI-free Python error fixer focused on common development issues.
"""

import sys
import subprocess
import re
import ast
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('autofix-python')


class PythonErrorFixer:
    """Core Python error fixing engine without AI dependencies"""
    
    def __init__(self):
        self.known_packages = {
            'requests': 'requests',
            'numpy': 'numpy', 
            'pandas': 'pandas',
            'matplotlib': 'matplotlib',
            'scipy': 'scipy',
            'sklearn': 'scikit-learn',
            'cv2': 'opencv-python',
            'PIL': 'Pillow',
            'yaml': 'PyYAML',
            'bs4': 'beautifulsoup4',
            'flask': 'Flask',
            'django': 'Django',
            'fastapi': 'fastapi',
            'sqlalchemy': 'SQLAlchemy',
            'pytest': 'pytest',
            'click': 'click',
            'rich': 'rich',
            'colorama': 'colorama',
            'tabulate': 'tabulate'
        }
        
        self.stdlib_modules = {
            'os', 'sys', 'json', 'csv', 'math', 'random', 'datetime', 
            'collections', 'itertools', 'functools', 'pathlib', 'typing',
            'logging', 'unittest', 're', 'subprocess', 'threading', 'asyncio'
        }
    
    def fix_script(self, script_path: str, max_retries: int = 3) -> bool:
        """Main entry point to fix a Python script"""
        logger.info(f"Fixing script: {script_path}")
        
        for attempt in range(max_retries):
            logger.info(f"Attempt {attempt + 1}/{max_retries}")
            
            # Run the script and capture errors
            result = self._run_script(script_path)
            
            if result['success']:
                logger.info("Script executed successfully!")
                return True
            
            # Try to fix the error
            if self._fix_error(result['error'], script_path):
                logger.info("Applied fix, retrying...")
                continue
            else:
                logger.error(f"Could not fix error: {result['error']}")
                break
        
        return False
    
    def _run_script(self, script_path: str) -> Dict:
        """Run a Python script and capture output/errors"""
        try:
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return {'success': True, 'output': result.stdout}
            else:
                return {'success': False, 'error': result.stderr}
                
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Script execution timeout'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _fix_error(self, error_text: str, script_path: str) -> bool:
        """Analyze error and apply appropriate fix"""
        
        # ModuleNotFoundError
        if "ModuleNotFoundError: No module named" in error_text:
            module_match = re.search(r"No module named '([^']+)'", error_text)
            if module_match:
                module_name = module_match.group(1)
                return self._fix_missing_module(module_name, script_path)
        
        # ImportError
        if "ImportError: cannot import name" in error_text:
            import_match = re.search(r"cannot import name '([^']+)' from '([^']+)'", error_text)
            if import_match:
                symbol, module = import_match.groups()
                return self._fix_import_error(symbol, module, script_path)
        
        # NameError
        if "NameError: name" in error_text and "is not defined" in error_text:
            name_match = re.search(r"name '([^']+)' is not defined", error_text)
            if name_match:
                undefined_name = name_match.group(1)
                return self._fix_name_error(undefined_name, script_path)
        
        # SyntaxError (basic fixes)
        if "SyntaxError:" in error_text:
            return self._fix_syntax_error(error_text, script_path)
        
        return False
    
    def _fix_missing_module(self, module_name: str, script_path: str) -> bool:
        """Fix missing module by installing package or creating local module"""
        
        # Check if it's a test/placeholder module
        if self._is_test_module(module_name):
            logger.warning(f"Module '{module_name}' appears to be a test/placeholder")
            logger.info("Recommendations:")
            logger.info("  1. Replace with a real package name")
            logger.info("  2. Install a package: pip install <package-name>")
            logger.info("  3. Create a local module file if intentional")
            return False
        
        # Try to install known package
        package_name = self.known_packages.get(module_name, module_name)
        if self._install_package(package_name):
            return True
        
        # Create local module file
        return self._create_local_module(module_name, script_path)
    
    def _fix_import_error(self, symbol: str, module: str, script_path: str) -> bool:
        """Fix import errors by commenting out invalid imports"""
        
        # Check if trying to import from stdlib
        if module.split('.')[0] in self.stdlib_modules:
            logger.warning(f"Cannot import '{symbol}' from stdlib module '{module}'")
            return self._comment_out_import(symbol, module, script_path)
        
        return False
    
    def _fix_name_error(self, name: str, script_path: str) -> bool:
        """Fix undefined names by creating placeholder functions"""
        
        script_file = Path(script_path)
        content = script_file.read_text(encoding='utf-8')
        
        # Add a simple placeholder function
        placeholder = f"""
def {name}(*args, **kwargs):
    \"\"\"Auto-generated placeholder function\"\"\"
    print(f"Called {name} with args={{args}}, kwargs={{kwargs}}")
    return None

"""
        
        # Add at the end of the file
        new_content = content + placeholder
        script_file.write_text(new_content, encoding='utf-8')
        
        logger.info(f"Created placeholder function: {name}")
        return True
    
    def _fix_syntax_error(self, error_text: str, script_path: str) -> bool:
        """Basic syntax error fixes"""
        
        script_file = Path(script_path)
        content = script_file.read_text(encoding='utf-8')
        
        # Fix missing colons
        if "expected ':'" in error_text or "invalid syntax" in error_text:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                stripped = line.strip()
                if (stripped.startswith(('if ', 'for ', 'while ', 'def ', 'class ')) and 
                    not stripped.endswith(':') and not stripped.endswith(':\\')):
                    lines[i] = line + ':'
                    logger.info(f"Added missing colon to line {i+1}")
            
            script_file.write_text('\n'.join(lines), encoding='utf-8')
            return True
        
        return False
    
    def _is_test_module(self, module_name: str) -> bool:
        """Check if module name appears to be a test/placeholder"""
        test_indicators = [
            'non_existent', 'nonexistent', 'fake', 'test', 'dummy',
            'placeholder', 'example', 'sample', 'mock', 'invalid'
        ]
        return any(indicator in module_name.lower() for indicator in test_indicators)
    
    def _install_package(self, package_name: str) -> bool:
        """Install a Python package using pip"""
        try:
            logger.info(f"Installing package: {package_name}")
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', package_name],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully installed {package_name}")
                return True
            else:
                logger.error(f"Failed to install {package_name}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error installing {package_name}: {e}")
            return False
    
    def _create_local_module(self, module_name: str, script_path: str) -> bool:
        """Create a local module file with basic structure"""
        
        script_dir = Path(script_path).parent
        module_file = script_dir / f"{module_name}.py"
        
        if module_file.exists():
            return True
        
        module_content = f'''"""
Auto-generated module: {module_name}
Created by AutoFix Python Engine
"""

def main():
    """Main function for {module_name}"""
    print("Module {module_name} loaded successfully")
    return True

# Add your functions here
'''
        
        module_file.write_text(module_content, encoding='utf-8')
        logger.info(f"Created local module: {module_file}")
        return True
    
    def _comment_out_import(self, symbol: str, module: str, script_path: str) -> bool:
        """Comment out problematic import statements"""
        
        script_file = Path(script_path)
        content = script_file.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if f"from {module} import" in line and symbol in line:
                lines[i] = f"# {line}  # Commented out by AutoFix - invalid import"
                logger.info(f"Commented out problematic import on line {i+1}")
                break
        
        script_file.write_text('\n'.join(lines), encoding='utf-8')
        return True


def main():
    """Command line interface"""
    if len(sys.argv) != 2:
        print("Usage: python autofix_python.py <script.py>")
        sys.exit(1)
    
    script_path = sys.argv[1]
    if not Path(script_path).exists():
        print(f"Error: Script '{script_path}' not found")
        sys.exit(1)
    
    print("AutoFix Python Engine - Pure Python Error Resolution")
    print("=" * 60)
    
    fixer = PythonErrorFixer()
    success = fixer.fix_script(script_path)
    
    if success:
        print("[SUCCESS] Script fixed successfully!")
        sys.exit(0)
    else:
        print("[FAILED] Could not fix all errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
