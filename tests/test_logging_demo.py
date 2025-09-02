#!/usr/bin/env python3
"""
Demo script to test new logging configuration and custom log levels
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from logging_utils import setup_logging, get_logger, temporary_log_level, ProgressLogger, AUTOFIX_SUCCESS, AUTOFIX_ATTEMPT
from metrics import log_duration
import logging


def test_custom_log_levels():
    """Test our custom AUTOFIX_SUCCESS and AUTOFIX_ATTEMPT log levels"""
    logger = get_logger('demo')
    
    print("\n=== Testing Custom Log Levels ===")
    logger.info("Starting custom log level tests...")
    
    # Test AUTOFIX_ATTEMPT level
    logger.attempt("Attempting to install missing package: requests")
    logger.attempt("Trying to fix import error...")
    
    # Test AUTOFIX_SUCCESS level  
    logger.success("Successfully installed requests package")
    logger.success("Import error fixed successfully")
    
    # Show hierarchy with other levels
    logger.debug("Debug message (level 10)")
    logger.attempt("Attempt message (level 15)")
    logger.info("Info message (level 20)")
    logger.success("Success message (level 25)")
    logger.warning("Warning message (level 30)")
    logger.error("Error message (level 40)")


def test_temporary_log_level():
    """Test the temporary_log_level context manager"""
    logger = get_logger('demo')
    
    print("\n=== Testing Temporary Log Level ===")
    logger.info("Normal log level - this should appear")
    logger.debug("Debug message - this should NOT appear normally")
    
    # Temporarily enable debug logging
    with temporary_log_level(logger, logging.DEBUG):
        logger.info("Inside context - debug enabled")
        logger.debug("Debug message - this SHOULD appear now")
        logger.attempt("Attempt message in debug context")
    
    logger.info("Back to normal log level")
    logger.debug("Debug message - this should NOT appear again")


def test_progress_logger():
    """Test the ProgressLogger class"""
    logger = get_logger('demo')
    
    print("\n=== Testing Progress Logger ===")
    progress = ProgressLogger(logger, total_steps=5)
    
    import time
    progress.step("Initializing AutoFix engine...")
    time.sleep(0.5)
    
    progress.step("Analyzing Python script...")
    time.sleep(0.5)
    
    progress.step("Detecting import errors...")
    time.sleep(0.5)
    
    progress.step("Installing missing packages...")
    time.sleep(0.5)
    
    progress.step("Applying fixes and running script...")
    time.sleep(0.5)
    
    logger.success("All operations completed!")


def test_log_duration():
    """Test the log_duration context manager"""
    logger = get_logger('demo')
    
    print("\n=== Testing Log Duration ===")
    
    # Example: Timing a fix operation
    with log_duration(logger, "Fixing imports"):
        import time
        time.sleep(0.5)  # Simulate work
    
    # Example: Timing package installation
    with log_duration(logger, "Installing packages"):
        time.sleep(0.3)  # Simulate pip install
    
    # Example: Timing script analysis
    with log_duration(logger, "Analyzing Python script"):
        time.sleep(0.2)  # Simulate parsing


def test_logging_with_colors():
    """Test colored logging output"""
    logger = get_logger('demo')
    
    print("\n=== Testing Colored Logging ===")
    logger.debug("Debug message (cyan)")
    logger.attempt("Attempt message (yellow)")
    logger.info("Info message (green)")
    logger.success("Success message (bright green)")
    logger.warning("Warning message (yellow)")
    logger.error("Error message (red)")
    logger.critical("Critical message (bright red)")


def main():
    """Main demo function"""
    print("AutoFix Logging Demo")
    print("=" * 50)
    
    # Setup logging with colors
    setup_logging(verbose=True, quiet=False, use_colors=True)
    logger = get_logger('demo')
    
    logger.info("Starting logging demonstration...")
    
    # Run all tests
    test_custom_log_levels()
    test_temporary_log_level()
    test_progress_logger()
    test_log_duration()
    test_logging_with_colors()
    
    print("\n" + "=" * 50)
    logger.success("Logging demo completed successfully!")


if __name__ == "__main__":
    main()