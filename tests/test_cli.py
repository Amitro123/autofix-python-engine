#!/usr/bin/env python3
"""
Tests for cli.py

Test the command-line interface functionality.
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli import AutoFixCLI


class TestAutoFixCLI(unittest.TestCase):
    """Test cases for AutoFixCLI"""
    
    def setUp(self):
        self.cli = AutoFixCLI()
        self.temp_dir = tempfile.mkdtemp()
        self.test_script = os.path.join(self.temp_dir, "test_script.py")
        
        # Create a simple test script
        with open(self.test_script, "w") as f:
            f.write("print('Hello, World!')")
    
    def tearDown(self):
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_parser(self):
        """Test argument parser creation"""
        parser = self.cli.create_parser()
        
        # Test that parser exists and has expected arguments
        self.assertIsNotNone(parser)
        
        # Test parsing valid arguments
        args = parser.parse_args([self.test_script])
        self.assertEqual(args.script_path, self.test_script)
        self.assertFalse(args.verbose)
        self.assertFalse(args.dry_run)
        self.assertEqual(args.max_retries, 3)
    
    def test_create_parser_with_options(self):
        """Test argument parser with various options"""
        parser = self.cli.create_parser()
        
        args = parser.parse_args([
            self.test_script,
            "--verbose",
            "--dry-run",
            "--max-retries", "5"
        ])
        
        self.assertEqual(args.script_path, self.test_script)
        self.assertTrue(args.verbose)
        self.assertTrue(args.dry_run)
        self.assertEqual(args.max_retries, 5)
    
    def test_validate_script_path_exists(self):
        """Test script path validation when file exists"""
        path = self.cli.validate_script_path(self.test_script)
        self.assertEqual(str(path), str(Path(self.test_script).resolve()))
    
    def test_validate_script_path_not_exists(self):
        """Test script path validation when file doesn't exist"""
        with self.assertRaises(FileNotFoundError):
            self.cli.validate_script_path("nonexistent_script.py")
    
    def test_validate_script_path_non_python(self):
        """Test script path validation with non-Python file"""
        txt_file = os.path.join(self.temp_dir, "test.txt")
        with open(txt_file, "w") as f:
            f.write("test content")
        
        # Should work but log a warning
        with patch.object(self.cli.logger, 'warning') as mock_warning:
            path = self.cli.validate_script_path(txt_file)
            mock_warning.assert_called_once()
            self.assertEqual(str(path), str(Path(txt_file).resolve()))
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_run_help(self, mock_stdout):
        """Test running CLI with no arguments shows help"""
        result = self.cli.run([])
        self.assertEqual(result, 0)
    
    @patch.object(AutoFixCLI, 'validate_script_path')
    @patch.object(AutoFixCLI, 'print_banner')
    @patch.object(AutoFixCLI, 'print_summary')
    def test_run_dry_run_mode(self, mock_summary, mock_banner, mock_validate):
        """Test dry run mode"""
        mock_validate.return_value = Path(self.test_script)
        
        result = self.cli.run([self.test_script, "--dry-run"])
        
        self.assertEqual(result, 0)
        mock_banner.assert_called_once()
        mock_summary.assert_not_called()  # No summary in dry run
    
    @patch.object(AutoFixCLI, 'validate_script_path')
    @patch.object(AutoFixCLI, 'print_banner')
    @patch.object(AutoFixCLI, 'print_summary')
    def test_run_quiet_mode(self, mock_summary, mock_banner, mock_validate):
        """Test quiet mode"""
        mock_validate.return_value = Path(self.test_script)
        
        # Mock the fixer to return success
        with patch.object(self.cli.fixer, 'run_script_with_fixes', return_value=True):
            result = self.cli.run([self.test_script, "--quiet"])
        
        self.assertEqual(result, 0)
        mock_banner.assert_not_called()  # No banner in quiet mode
        mock_summary.assert_not_called()  # No summary in quiet mode
    
    @patch.object(AutoFixCLI, 'validate_script_path')
    def test_run_script_success(self, mock_validate):
        """Test successful script execution"""
        mock_validate.return_value = Path(self.test_script)
        
        # Mock the fixer to return success
        with patch.object(self.cli.fixer, 'run_script_with_fixes', return_value=True):
            result = self.cli.run([self.test_script])
        
        self.assertEqual(result, 0)
    
    @patch.object(AutoFixCLI, 'validate_script_path')
    def test_run_script_failure(self, mock_validate):
        """Test failed script execution"""
        mock_validate.return_value = Path(self.test_script)
        
        # Mock the fixer to return failure
        with patch.object(self.cli.fixer, 'run_script_with_fixes', return_value=False):
            result = self.cli.run([self.test_script])
        
        self.assertEqual(result, 1)
    
    def test_run_keyboard_interrupt(self):
        """Test handling of keyboard interrupt"""
        with patch.object(self.cli.fixer, 'run_script_with_fixes', side_effect=KeyboardInterrupt):
            with patch.object(self.cli, 'validate_script_path', return_value=Path(self.test_script)):
                result = self.cli.run([self.test_script])
        
        self.assertEqual(result, 130)
    
    def test_run_unexpected_error(self):
        """Test handling of unexpected errors"""
        with patch.object(self.cli.fixer, 'run_script_with_fixes', side_effect=RuntimeError("Test error")):
            with patch.object(self.cli, 'validate_script_path', return_value=Path(self.test_script)):
                result = self.cli.run([self.test_script])
        
        self.assertEqual(result, 1)
    
    def test_logging_levels(self):
        """Test logging level configuration and custom log levels"""
        from logging_utils import setup_logging, get_logger, AUTOFIX_SUCCESS, AUTOFIX_ATTEMPT
        import logging
        
        # Test verbose mode
        with patch('cli.setup_logging') as mock_setup:
            with patch.object(self.cli, 'validate_script_path', return_value=Path(self.test_script)):
                with patch.object(self.cli.fixer, 'run_script_with_fixes', return_value=True):
                    self.cli.run([self.test_script, "--verbose"])
        
        mock_setup.assert_called_with(verbose=True, quiet=False, use_colors=True)
        
        # Test quiet mode
        with patch('cli.setup_logging') as mock_setup:
            with patch.object(self.cli, 'validate_script_path', return_value=Path(self.test_script)):
                with patch.object(self.cli.fixer, 'run_script_with_fixes', return_value=True):
                    self.cli.run([self.test_script, "--quiet"])
        
        mock_setup.assert_called_with(verbose=False, quiet=True, use_colors=True)
        
        # Test custom log levels are properly registered
        self.assertEqual(AUTOFIX_SUCCESS, 25)
        self.assertEqual(AUTOFIX_ATTEMPT, 15)
        
        # Test that custom methods exist on logger
        logger = get_logger('test')
        self.assertTrue(hasattr(logger, 'success'))
        self.assertTrue(hasattr(logger, 'attempt'))
        
        # Test log level hierarchy
        self.assertLess(logging.DEBUG, AUTOFIX_ATTEMPT)
        self.assertLess(AUTOFIX_ATTEMPT, logging.INFO)
        self.assertLess(logging.INFO, AUTOFIX_SUCCESS)
        self.assertLess(AUTOFIX_SUCCESS, logging.WARNING)


if __name__ == "__main__":
    unittest.main()