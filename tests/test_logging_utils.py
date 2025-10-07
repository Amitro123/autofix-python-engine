#!/usr/bin/env python3
"""
Tests for logging_utils.py

Test the logging utilities including custom log levels, ProgressLogger, and temporary_log_level.
"""

import unittest
import logging
import sys
from pathlib import Path
from io import StringIO
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from autofix.helpers.logging_utils import (
    setup_logging, get_logger, temporary_log_level, ProgressLogger,
    AUTOFIX_SUCCESS, AUTOFIX_ATTEMPT, AutoFixFormatter
)


class TestLoggingUtils(unittest.TestCase):
    """Test cases for logging utilities"""
    
    def setUp(self):
        """Set up test environment"""
        # Clear any existing handlers
        logging.getLogger().handlers.clear()
        
    def test_custom_log_levels(self):
        """Test custom log level constants"""
        self.assertEqual(AUTOFIX_SUCCESS, 25)
        self.assertEqual(AUTOFIX_ATTEMPT, 15)
        
        # Test hierarchy
        self.assertLess(logging.DEBUG, AUTOFIX_ATTEMPT)
        self.assertLess(AUTOFIX_ATTEMPT, logging.INFO)
        self.assertLess(logging.INFO, AUTOFIX_SUCCESS)
        self.assertLess(AUTOFIX_SUCCESS, logging.WARNING)
    
    def test_logger_custom_methods(self):
        """Test that loggers have custom success() and attempt() methods"""
        logger = get_logger('test')
        
        # Test methods exist
        self.assertTrue(hasattr(logger, 'success'))
        self.assertTrue(hasattr(logger, 'attempt'))
        self.assertTrue(callable(logger.success))
        self.assertTrue(callable(logger.attempt))
    
    def test_get_logger(self):
        """Test get_logger function"""
        # Test with autofix prefix
        logger1 = get_logger('autofix.test')
        self.assertEqual(logger1.name, 'autofix.test')
        
        # Test without autofix prefix (should be added)
        logger2 = get_logger('test')
        self.assertEqual(logger2.name, 'autofix.test')
        
        # Should return same logger instance
        self.assertIs(logger1, logger2)
    
    def test_temporary_log_level(self):
        """Test temporary_log_level context manager"""
        logger = get_logger('test')
        original_level = logging.INFO
        logger.setLevel(original_level)
        
        # Test level change and restoration
        with temporary_log_level(logger, logging.DEBUG):
            self.assertEqual(logger.level, logging.DEBUG)
        
        self.assertEqual(logger.level, original_level)
    
    def test_temporary_log_level_with_exception(self):
        """Test temporary_log_level restores level even with exception"""
        logger = get_logger('test')
        original_level = logging.INFO
        logger.setLevel(original_level)
        
        try:
            with temporary_log_level(logger, logging.DEBUG):
                self.assertEqual(logger.level, logging.DEBUG)
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Level should be restored despite exception
        self.assertEqual(logger.level, original_level)
    
    def test_progress_logger(self):
        """Test ProgressLogger class"""
        # Capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        
        logger = get_logger('test')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Test progress logging
        progress = ProgressLogger(logger, total_steps=4)
        
        progress.step("Step 1")
        progress.step("Step 2")
        progress.step("Step 3")
        progress.step("Step 4")
        
        # Check output contains progress percentages
        output = stream.getvalue()
        self.assertIn("[ 25.0%]", output)
        self.assertIn("[ 50.0%]", output)
        self.assertIn("[ 75.0%]", output)
        self.assertIn("[100.0%]", output)
        self.assertIn("Step 1", output)
        self.assertIn("Step 4", output)
    
    def test_autofix_formatter_colors(self):
        """Test AutoFixFormatter with colors"""
        formatter = AutoFixFormatter(use_colors=True)
        
        # Test that formatter has color mappings
        self.assertIn('SUCCESS', formatter.COLORS)
        self.assertIn('ATTEMPT', formatter.COLORS)
        self.assertIn('ERROR', formatter.COLORS)
    
    def test_autofix_formatter_no_colors(self):
        """Test AutoFixFormatter without colors"""
        formatter = AutoFixFormatter(use_colors=False)
        
        # Test that colors are disabled
        self.assertFalse(formatter.use_colors)
        self.assertEqual(formatter.COLORS, {})
    
    def test_setup_logging_verbose(self):
        """Test setup_logging with verbose mode"""
        logger = setup_logging(verbose=True, quiet=False, use_colors=False)
        
        self.assertEqual(logger.level, logging.DEBUG)
        self.assertGreater(len(logger.handlers), 0)
    
    def test_setup_logging_quiet(self):
        """Test setup_logging with quiet mode"""
        logger = setup_logging(verbose=False, quiet=True, use_colors=False)
        
        self.assertEqual(logger.level, logging.WARNING)
        self.assertGreater(len(logger.handlers), 0)
    
    def test_setup_logging_normal(self):
        """Test setup_logging with normal mode"""
        logger = setup_logging(verbose=False, quiet=False, use_colors=False)
        
        self.assertEqual(logger.level, logging.INFO)
        self.assertGreater(len(logger.handlers), 0)
    
    @patch('logging_utils.COLORAMA_AVAILABLE', False)
    def test_formatter_fallback_no_colorama(self):
        """Test formatter fallback when colorama is not available"""
        formatter = AutoFixFormatter(use_colors=True)
        
        # Should fallback to no colors
        self.assertFalse(formatter.use_colors)
        self.assertEqual(formatter.COLORS, {})


class TestProgressLoggerEdgeCases(unittest.TestCase):
    """Test edge cases for ProgressLogger"""
    
    def test_progress_logger_zero_steps(self):
        """Test ProgressLogger with zero steps"""
        logger = get_logger('test')
        
        # Should not crash with zero steps
        progress = ProgressLogger(logger, total_steps=0)
        
        # This would cause division by zero, but should be handled gracefully
        with self.assertRaises(ZeroDivisionError):
            progress.step("This should fail")
    
    def test_progress_logger_more_steps_than_total(self):
        """Test ProgressLogger with more steps than total"""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        
        logger = get_logger('test')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        progress = ProgressLogger(logger, total_steps=2)
        
        progress.step("Step 1")  # 50%
        progress.step("Step 2")  # 100%
        progress.step("Step 3")  # 150%
        
        output = stream.getvalue()
        self.assertIn("[ 50.0%]", output)
        self.assertIn("[100.0%]", output)
        self.assertIn("[150.0%]", output)  # Should allow over 100%


if __name__ == "__main__":
    unittest.main()
