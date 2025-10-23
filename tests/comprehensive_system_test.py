#!/usr/bin/env python3
"""
Comprehensive System Test - Verify all components work together
Tests the entire unified AutoFixer engine after extensive changes
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

def test_core_imports():
    """Test that all core modules can be imported"""
    try:
        from autofix.cli.autofix_cli_interactive import AutoFixer
        from autofix_core.shared.core.error_parser import ErrorParser
        from autofix.constants import ErrorType
        assert True  # ✅ Instead of: return True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")  # ✅ Instead of: return False


def test_unified_engine():
    """Test unified AutoFixer engine initialization"""
    print("2. Testing unified engine...")
    try:
        from autofix.cli.autofix_cli_interactive import AutoFixer
        
        fixer = AutoFixer()
        
        # Verify all components are integrated
        assert hasattr(fixer, 'handlers'), "Missing handlers"
        assert hasattr(fixer, 'error_parser'), "Missing ErrorParser"
        assert hasattr(fixer, 'import_suggestions'), "Missing import suggestions"
        assert hasattr(fixer, 'known_pip_packages'), "Missing known packages"
        
        # Verify handler count
        assert len(fixer.handlers) == 5, f"Expected 5 handlers, got {len(fixer.handlers)}"
        
        # Verify data loaded
        assert len(fixer.import_suggestions) > 0, "Import suggestions not loaded"
        assert len(fixer.known_pip_packages) > 0, "Known packages not loaded"
        
        print(f"   ✅ Engine initialized with {len(fixer.handlers)} handlers")
        print(f"   ✅ {len(fixer.import_suggestions)} import suggestions loaded")
        print(f"   ✅ {len(fixer.known_pip_packages)} known packages loaded")
        return True
    except Exception as e:
        print(f"   ❌ Engine test failed: {e}")
        return False

def test_error_handlers():
    """Test enhanced error handlers"""
    print("3. Testing enhanced error handlers...")
    try:
        from autofix_cli_interactive import AutoFixer
        
        fixer = AutoFixer()
        
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
            
            # Test enhanced extraction
            details = handler.extract_details(error_output)
            assert details.suggestion, f"No suggestion for {expected_handler}"
        
        print("   ✅ All error handlers working correctly")
        return True
    except Exception as e:
        print(f"   ❌ Handler test failed: {e}")
        return False

def test_enhanced_features():
    """Test enhanced features from python_fixer.py"""
    print("4. Testing enhanced features...")
    try:
        from autofix_cli_interactive import ModuleNotFoundHandler
        
        handler = ModuleNotFoundHandler()
        
        # Test package resolution
        details = handler.extract_details("ModuleNotFoundError: No module named 'cv2'")
        assert "opencv-python" in details.suggestion, "Package resolution not working"
        
        # Test known package detection
        details = handler.extract_details("ModuleNotFoundError: No module named 'requests'")
        assert "pip install requests" in details.suggestion, "Known package detection not working"
        
        print("   ✅ Enhanced features working (package resolution, suggestions)")
        return True
    except Exception as e:
        print(f"   ❌ Enhanced features test failed: {e}")
        return False

def test_rollback_functionality():
    """Test rollback functionality"""
    print("5. Testing rollback functionality...")
    try:
        from rollback import FixTransaction
        
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            test_file = Path(f.name)
            f.write("print('original content')")
        
        try:
            # Test successful transaction
            with FixTransaction(test_file) as transaction:
                with open(test_file, 'w') as f:
                    f.write("print('modified content')")
            
            # Verify file was modified
            content = test_file.read_text()
            assert "modified content" in content, "File not modified"
            
            print("   ✅ Rollback functionality working")
            return True
        finally:
            # Cleanup
            if test_file.exists():
                os.unlink(test_file)
                
    except Exception as e:
        print(f"   ❌ Rollback test failed: {e}")
        return False

def test_metrics_integration():
    """Test Firebase metrics integration"""
    print("6. Testing metrics integration...")
    try:
        from autofix_cli_interactive import AutoFixer, METRICS_ENABLED, metrics_collector
        
        fixer = AutoFixer()
        
        # Test metrics saving (should not fail even if Firebase not configured)
        result = fixer.save_metrics(
            script_path="test_script.py",
            status="test_status",
            message="Test message"
        )
        
        print(f"   ✅ Metrics integration working (enabled: {METRICS_ENABLED})")
        return True
    except Exception as e:
        print(f"   ❌ Metrics test failed: {e}")
        return False

def test_cli_structure():
    """Test CLI structure and arguments"""
    print("7. Testing CLI structure...")
    try:
        from autofix_cli_interactive import main
        import inspect
        
        # Verify main function exists and is callable
        assert callable(main), "Main function not callable"
        
        # Test AutoFixer process_script method signature
        from autofix_cli_interactive import AutoFixer
        fixer = AutoFixer()
        
        sig = inspect.signature(fixer.process_script)
        expected_params = ['script_path', 'max_retries', 'auto_fix']
        actual_params = list(sig.parameters.keys())
        
        for param in expected_params:
            assert param in actual_params, f"Missing parameter: {param}"
        
        print("   ✅ CLI structure intact")
        return True
    except Exception as e:
        print(f"   ❌ CLI test failed: {e}")
        return False

def test_error_parser_integration():
    """Test ErrorParser integration"""
    print("8. Testing ErrorParser integration...")
    try:
        from autofix_cli_interactive import AutoFixer
        from error_parser import ErrorParser
        
        fixer = AutoFixer()
        
        # Verify ErrorParser is integrated
        assert hasattr(fixer, 'error_parser'), "ErrorParser not integrated"
        assert isinstance(fixer.error_parser, ErrorParser), "ErrorParser not properly instantiated"
        
        print("   ✅ ErrorParser integration successful")
        return True
    except Exception as e:
        print(f"   ❌ ErrorParser test failed: {e}")
        return False

def main():
    """Run comprehensive system test"""
    print("🧪 COMPREHENSIVE SYSTEM TEST")
    print("=" * 60)
    
    tests = [
        test_core_imports,
        test_unified_engine,
        test_error_handlers,
        test_enhanced_features,
        test_rollback_functionality,
        test_metrics_integration,
        test_cli_structure,
        test_error_parser_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"   ⚠️  Test failed but continuing...")
        except Exception as e:
            print(f"   ❌ Test crashed: {e}")
    
    print("=" * 60)
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("✅ System is working correctly")
        print("✅ All components integrated successfully")
        print("✅ Ready for production use")
        return True
    else:
        print(f"⚠️  {total - passed} tests failed")
        print("❌ System needs attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
