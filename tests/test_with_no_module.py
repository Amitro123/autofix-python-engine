#!/usr/bin/env python3
"""
Test script that intentionally imports a non-existent module.
This is used to test AutoFix's module fixing capabilities.
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from python_fixer import PythonFixer


class TestWithNoModule(unittest.TestCase):
    """Test AutoFix with missing module scenarios"""
    
    def test_missing_module_detection(self):
        """Test that missing modules are properly detected"""
        fixer = PythonFixer()
        
        # This would normally cause ModuleNotFoundError
        # but we're testing the detection mechanism
        self.assertTrue(hasattr(fixer, '_is_known_pip_package'))
        self.assertFalse(fixer._is_known_pip_package('a_non_existent_module'))


if __name__ == "__main__":
    unittest.main()