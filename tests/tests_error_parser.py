#!/usr/bin/env python3
"""
Tests for error_parser.py

Test the structured parsing of Python errors into ParsedError objects.
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from error_parser import ErrorParser, ParsedError


class TestErrorParser(unittest.TestCase):
    """Test cases for ErrorParser"""
    
    def setUp(self):
        self.parser = ErrorParser()
        self.test_script = "/test/script.py"
    
    def test_parse_module_not_found_error(self):
        """Test parsing ModuleNotFoundError"""
        error = ModuleNotFoundError("No module named 'requests'")
        error.name = "requests"
        
        parsed = self.parser.parse_exception(error, self.test_script)
        
        self.assertEqual(parsed.error_type, "ModuleNotFoundError")
        self.assertEqual(parsed.missing_module, "requests")
        self.assertEqual(parsed.file_path, self.test_script)
    
    def test_parse_import_error_cannot_import(self):
        """Test parsing ImportError with 'cannot import name' pattern"""
        error = ImportError("cannot import name 'sleep' from 'time'")
        
        parsed = self.parser.parse_exception(error, self.test_script)
        
        self.assertEqual(parsed.error_type, "ImportError")
        self.assertEqual(parsed.missing_function, "sleep")
        self.assertEqual(parsed.missing_module, "time")
    
    def test_parse_import_error_no_module(self):
        """Test parsing ImportError with 'No module named' pattern"""
        error = ImportError("No module named 'pandas'")
        
        parsed = self.parser.parse_exception(error, self.test_script)
        
        self.assertEqual(parsed.error_type, "ImportError")
        self.assertEqual(parsed.missing_module, "pandas")
    
    def test_parse_name_error(self):
        """Test parsing NameError"""
        error = NameError("name 'calculate_something' is not defined")
        
        parsed = self.parser.parse_exception(error, self.test_script)
        
        self.assertEqual(parsed.error_type, "NameError")
        self.assertEqual(parsed.missing_function, "calculate_something")
    
    def test_parse_attribute_error(self):
        """Test parsing AttributeError"""
        error = AttributeError("'math' object has no attribute 'sqrt'")
        
        parsed = self.parser.parse_exception(error, self.test_script)
        
        self.assertEqual(parsed.error_type, "AttributeError")
        self.assertEqual(parsed.missing_module, "math")
        self.assertEqual(parsed.missing_attribute, "sqrt")
    
    def test_parse_syntax_error_basic(self):
        """Test parsing basic SyntaxError"""
        error = SyntaxError("invalid syntax")
        error.lineno = 10
        error.text = "print('hello'"
        
        parsed = self.parser.parse_exception(error, self.test_script)
        
        self.assertEqual(parsed.error_type, "SyntaxError")
        self.assertEqual(parsed.line_number, 10)
        self.assertIsNotNone(parsed.syntax_details)
    
    def test_detect_fstring_version_issue(self):
        """Test detection of f-string version compatibility issue"""
        # Mock older Python version
        original_version = self.parser.python_version
        self.parser.python_version = (3, 5)  # Before f-strings
        
        try:
            version_issue = self.parser._detect_version_syntax_issue("invalid syntax f'hello'")
            
            self.assertIsNotNone(version_issue)
            self.assertEqual(version_issue["feature"], "f-strings")
            self.assertEqual(version_issue["required_version"], "3.6+")
        finally:
            self.parser.python_version = original_version
    
    def test_detect_walrus_version_issue(self):
        """Test detection of walrus operator version compatibility issue"""
        # Mock older Python version
        original_version = self.parser.python_version
        self.parser.python_version = (3, 7)  # Before walrus operator
        
        try:
            version_issue = self.parser._detect_version_syntax_issue("invalid syntax :=")
            
            self.assertIsNotNone(version_issue)
            self.assertEqual(version_issue["feature"], "walrus operator (:=)")
            self.assertEqual(version_issue["required_version"], "3.8+")
        finally:
            self.parser.python_version = original_version


if __name__ == "__main__":
    unittest.main()
