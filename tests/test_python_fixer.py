#!/usr/bin/env python3
"""
Tests for python_fixer.py

Test the core Python error fixing functionality.
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from autofix.python_fixer import PythonFixer
from autofix.error_parser import ParsedError


class TestPythonFixer(unittest.TestCase):
    """Test cases for PythonFixer"""
    
    def setUp(self):
        self.fixer = PythonFixer()
        self.temp_dir = tempfile.mkdtemp()
        self.test_script = os.path.join(self.temp_dir, "test_script.py")
    
    def tearDown(self):
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_is_known_pip_package(self):
        """Test identification of known pip packages"""
        self.assertTrue(self.fixer._is_known_pip_package("requests"))
        self.assertTrue(self.fixer._is_known_pip_package("numpy"))
        self.assertTrue(self.fixer._is_known_pip_package("pandas"))
        self.assertFalse(self.fixer._is_known_pip_package("nonexistent_package"))
    
    def test_is_known_pip_package_aliases(self):
        """Test identification of package aliases"""
        self.assertTrue(self.fixer._is_known_pip_package("cv2"))  # opencv-python
        self.assertTrue(self.fixer._is_known_pip_package("PIL"))  # pillow
        self.assertTrue(self.fixer._is_known_pip_package("bs4"))  # beautifulsoup4
    
    def test_suggest_library_import(self):
        """Test library import suggestions"""
        self.assertEqual(self.fixer._suggest_library_import("sleep"), "from time import sleep")
        self.assertEqual(self.fixer._suggest_library_import("json"), "import json")
        self.assertEqual(self.fixer._suggest_library_import("sqrt"), "from math import sqrt")
        self.assertEqual(self.fixer._suggest_library_import("isfile"), "from os.path import isfile")
        self.assertIsNone(self.fixer._suggest_library_import("unknown_function"))
    
    def test_analyze_function_usage(self):
        """Test function usage analysis for parameter inference"""
        content = """
def main():
    result = calculate_something(10, 20)
    print(result)
"""
        params = self.fixer._analyze_function_usage("calculate_something", content)
        self.assertEqual(params, ["arg1", "arg2"])
    
    def test_analyze_function_usage_no_params(self):
        """Test function usage analysis with no parameters"""
        content = """
def main():
    result = get_value()
    print(result)
"""
        params = self.fixer._analyze_function_usage("get_value", content)
        self.assertEqual(params, [])
    
    def test_add_import_to_script(self):
        """Test adding import statement to script"""
        # Create test script
        script_content = """#!/usr/bin/env python3
import os

def main():
    print("Hello")
"""
        with open(self.test_script, "w") as f:
            f.write(script_content)
        
        # Add import
        success = self.fixer._add_import_to_script("import json", self.test_script)
        self.assertTrue(success)
        
        # Check that import was added
        with open(self.test_script, "r") as f:
            content = f.read()
        
        self.assertIn("import json", content)
        self.assertIn("import os", content)  # Original import should still be there
    
    def test_add_import_to_script_duplicate(self):
        """Test adding duplicate import to script"""
        # Create test script with existing import
        script_content = """#!/usr/bin/env python3
import json

def main():
    print("Hello")
"""
        with open(self.test_script, "w") as f:
            f.write(script_content)
        
        # Try to add same import
        success = self.fixer._add_import_to_script("import json", self.test_script)
        self.assertTrue(success)  # Should succeed but not duplicate
        
        # Check that import appears only once
        with open(self.test_script, "r") as f:
            content = f.read()
        
        self.assertEqual(content.count("import json"), 1)
    
    def test_create_function_in_script(self):
        """Test creating missing function in script"""
        # Create test script
        script_content = """#!/usr/bin/env python3

def main():
    result = calculate_something(10, 20)
    print(result)

if __name__ == "__main__":
    main()
"""
        with open(self.test_script, "w") as f:
            f.write(script_content)
        
        # Create function
        success = self.fixer._create_function_in_script("calculate_something", self.test_script)
        self.assertTrue(success)
        
        # Check that function was created
        with open(self.test_script, "r") as f:
            content = f.read()
        
        self.assertIn("def calculate_something(arg1, arg2):", content)
        self.assertIn("Auto-generated function by AutoFix", content)
    
    def test_create_function_in_script_already_exists(self):
        """Test creating function that already exists"""
        # Create test script with existing function
        script_content = """#!/usr/bin/env python3

def calculate_something(a, b):
    return a + b

def main():
    result = calculate_something(10, 20)
    print(result)
"""
        with open(self.test_script, "w") as f:
            f.write(script_content)
        
        # Try to create function that already exists
        success = self.fixer._create_function_in_script("calculate_something", self.test_script)
        self.assertFalse(success)  # Should fail because function exists
    
    def test_create_missing_file(self):
        """Test creating missing module file"""
        success = self.fixer._create_missing_file("test_module", self.test_script)
        self.assertTrue(success)
        
        # Check that file was created
        module_file = os.path.join(self.temp_dir, "test_module.py")
        self.assertTrue(os.path.exists(module_file))
        
        # Check file content
        with open(module_file, "r") as f:
            content = f.read()
        
        self.assertIn("Auto-generated module by AutoFix", content)
        self.assertIn("def placeholder_function():", content)
    
    def test_fix_module_not_found_error(self):
        """Test fixing ModuleNotFoundError"""
        error = ParsedError(
            error_type="ModuleNotFoundError",
            error_message="No module named 'test_module'",
            file_path=self.test_script,
            missing_module="test_module"
        )
        
        # Should create local file since it's not a known pip package
        success = self.fixer._fix_module_not_found(error)
        self.assertTrue(success)
        
        # Check that file was created
        module_file = os.path.join(self.temp_dir, "test_module.py")
        self.assertTrue(os.path.exists(module_file))
    
    def test_fix_name_error_common_function(self):
        """Test fixing NameError for common function"""
        # Create test script
        with open(self.test_script, "w") as f:
            f.write("print('test')")
        
        error = ParsedError(
            error_type="NameError",
            error_message="name 'sleep' is not defined",
            file_path=self.test_script,
            missing_function="sleep"
        )
        
        success = self.fixer._fix_name_error(error)
        self.assertTrue(success)
        
        # Check that import was added
        with open(self.test_script, "r") as f:
            content = f.read()
        
        self.assertIn("from time import sleep", content)
    
    def test_fix_name_error_create_function(self):
        """Test fixing NameError by creating function"""
        # Create test script
        script_content = """#!/usr/bin/env python3

def main():
    result = custom_function(42)
    print(result)
"""
        with open(self.test_script, "w") as f:
            f.write(script_content)
        
        error = ParsedError(
            error_type="NameError",
            error_message="name 'custom_function' is not defined",
            file_path=self.test_script,
            missing_function="custom_function"
        )
        
        success = self.fixer._fix_name_error(error)
        self.assertTrue(success)
        
        # Check that function was created
        with open(self.test_script, "r") as f:
            content = f.read()
        
        self.assertIn("def custom_function(arg1):", content)
    
    @patch('subprocess.run')
    def test_install_package_success(self, mock_run):
        """Test successful package installation"""
        # Mock successful pip install
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""
        
        success = self.fixer._install_package("requests")
        self.assertTrue(success)
        
        # Check that pip was called correctly
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn("pip", args)
        self.assertIn("install", args)
        self.assertIn("requests", args)
    
    @patch('subprocess.run')
    def test_install_package_failure(self, mock_run):
        """Test failed package installation"""
        # Mock failed pip install
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Package not found"
        
        success = self.fixer._install_package("nonexistent_package")
        self.assertFalse(success)
    
    @patch('subprocess.run')
    def test_install_package_with_alias(self, mock_run):
        """Test package installation with alias mapping"""
        # Mock successful pip install
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""
        
        success = self.fixer._install_package("cv2")
        self.assertTrue(success)
        
        # Check that the correct package name was used
        args = mock_run.call_args[0][0]
        self.assertIn("opencv-python", args)
        self.assertNotIn("cv2", args)


if __name__ == "__main__":
    unittest.main()