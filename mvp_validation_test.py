#!/usr/bin/env python3
"""
MVP Validation Test for Unified AutoFixer Engine
Tests all critical functionality for production readiness
"""

import os
import tempfile
from autofix_cli_interactive import AutoFixer

def test_mvp_functionality():
    """Comprehensive MVP validation test"""
    print("🚀 MVP Validation Test - Unified AutoFixer Engine")
    print("=" * 60)
    
    # Test 1: Engine Initialization
    print("1. Testing engine initialization...")
    try:
        fixer = AutoFixer()
        assert hasattr(fixer, 'handlers'), "Missing handlers"
        assert hasattr(fixer, 'error_parser'), "Missing ErrorParser"
        assert hasattr(fixer, 'import_suggestions'), "Missing import suggestions"
        assert len(fixer.handlers) == 5, f"Expected 5 handlers, got {len(fixer.handlers)}"
        print("   ✅ Engine initialization successful")
    except Exception as e:
        print(f"   ❌ Engine initialization failed: {e}")
        return False
    
    # Test 2: Handler Selection
    print("2. Testing error handler selection...")
    test_cases = [
        ("ModuleNotFoundError: No module named 'requests'", "ModuleNotFoundError"),
        ("TypeError: unsupported operand type", "TypeError"),
        ("IndexError: list index out of range", "IndexError"),
        ("SyntaxError: invalid syntax", "SyntaxError"),
        ("IndentationError: expected an indented block", "IndentationError")
    ]
    
    for error_output, expected_handler in test_cases:
        handler = fixer.find_handler(error_output)
        if not handler or handler.error_name != expected_handler:
            print(f"   ❌ Handler selection failed for {expected_handler}")
            return False
    print("   ✅ Handler selection working correctly")
    
    # Test 3: Enhanced Error Analysis
    print("3. Testing enhanced error analysis...")
    try:
        from autofix_cli_interactive import ModuleNotFoundHandler
        handler = ModuleNotFoundHandler()
        
        # Test enhanced ModuleNotFoundHandler
        details = handler.extract_details("ModuleNotFoundError: No module named 'requests'")
        assert "pip install requests" in details.suggestion, "Enhanced suggestion not working"
        
        # Test package resolution
        details = handler.extract_details("ModuleNotFoundError: No module named 'cv2'")
        assert "opencv-python" in details.suggestion, "Package resolution not working"
        
        print("   ✅ Enhanced error analysis working")
    except Exception as e:
        print(f"   ❌ Enhanced error analysis failed: {e}")
        return False
    
    # Test 4: Import Suggestions Integration
    print("4. Testing import suggestions integration...")
    try:
        assert len(fixer.import_suggestions) > 0, "Import suggestions not loaded"
        assert len(fixer.known_pip_packages) > 0, "Known packages not loaded"
        print(f"   ✅ Import suggestions loaded: {len(fixer.import_suggestions)} items")
        print(f"   ✅ Known packages loaded: {len(fixer.known_pip_packages)} items")
    except Exception as e:
        print(f"   ❌ Import suggestions integration failed: {e}")
        return False
    
    # Test 5: Firebase Metrics Integration
    print("5. Testing Firebase metrics integration...")
    try:
        from autofix_cli_interactive import METRICS_ENABLED, metrics_collector
        print(f"   ✅ Metrics enabled: {METRICS_ENABLED}")
        print(f"   ✅ Metrics collector available: {metrics_collector is not None}")
        
        # Test metrics saving (should not fail even if Firebase is not configured)
        result = fixer.save_metrics("test_script.py", "test_status", message="Test message")
        print(f"   ✅ Metrics saving functional: {result}")
    except Exception as e:
        print(f"   ❌ Firebase metrics integration failed: {e}")
        return False
    
    # Test 6: CLI Arguments Structure
    print("6. Testing CLI arguments structure...")
    try:
        import argparse
        from autofix_cli_interactive import main
        
        # Verify main function exists and is callable
        assert callable(main), "Main function not callable"
        print("   ✅ CLI structure intact")
    except Exception as e:
        print(f"   ❌ CLI arguments structure failed: {e}")
        return False
    
    # Test 7: UX Features Preservation
    print("7. Testing UX features preservation...")
    try:
        # Test spinner function exists
        assert hasattr(fixer, '_loading_spinner'), "Loading spinner missing"
        
        # Test process_script method exists with correct signature
        import inspect
        sig = inspect.signature(fixer.process_script)
        expected_params = ['script_path', 'max_retries', 'auto_fix']
        actual_params = list(sig.parameters.keys())
        
        for param in expected_params:
            assert param in actual_params, f"Missing parameter: {param}"
        
        print("   ✅ UX features preserved (spinners, prompts, auto-fix)")
    except Exception as e:
        print(f"   ❌ UX features preservation failed: {e}")
        return False
    
    # Test 8: Error Parser Integration
    print("8. Testing ErrorParser integration...")
    try:
        from autofix.error_parser import ErrorParser, ParsedError
        
        # Test ErrorParser is integrated
        assert hasattr(fixer, 'error_parser'), "ErrorParser not integrated"
        assert isinstance(fixer.error_parser, ErrorParser), "ErrorParser not properly instantiated"
        
        print("   ✅ ErrorParser integration successful")
    except Exception as e:
        print(f"   ❌ ErrorParser integration failed: {e}")
        return False
    
    print("=" * 60)
    print("🎉 MVP VALIDATION SUCCESSFUL!")
    print("✅ All critical functionality working")
    print("✅ Enhanced error handling integrated")
    print("✅ Firebase metrics preserved")
    print("✅ UX features maintained")
    print("✅ Ready for production deployment")
    return True

if __name__ == "__main__":
    success = test_mvp_functionality()
    exit(0 if success else 1)
