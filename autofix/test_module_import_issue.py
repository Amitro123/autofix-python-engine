#!/usr/bin/env python3
"""
Test script to demonstrate module import issue that AutoFix should handle
"""

import unittest
from test_cli import TestAutoFixCLI

def main():
    # This should cause ModuleNotFoundError: No module named 'test_cli'
    # AutoFix should detect this and fix the import path to 'tests.test_cli'
    suite = unittest.TestSuite()
    suite.addTest(TestAutoFixCLI('test_run_dry_run_mode'))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print(f"Test completed: {result.wasSuccessful()}")

if __name__ == "__main__":
    main()
