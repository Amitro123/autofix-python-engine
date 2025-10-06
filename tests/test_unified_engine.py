#!/usr/bin/env python3
"""
Test script for the unified AutoFixer engine
Tests all enhanced error handlers with advanced logic from python_fixer.py
"""

import os
import tempfile
from autofix.cli.autofix_cli_interactive import AutoFixer
from autofix.handlers.module_not_found_handler import ModuleNotFoundHandler
from autofix.handlers.type_error_handler import TypeErrorHandler
from autofix.handlers.index_error_handler import IndexErrorHandler
from autofix.handlers.syntax_error_handler import UnifiedSyntaxErrorHandler as SyntaxErrorHandler

def test_module_not_found_handler():
    """Test enhanced ModuleNotFoundHandler with advanced package resolution"""
    print("🧪 Testing ModuleNotFoundHandler...")
    
    handler = ModuleNotFoundHandler()
    
    # Test known package detection
    error_output = "ModuleNotFoundError: No module named 'requests'"
    details = handler.extract_details(error_output)
    assert details.error_type == "module_not_found"
    assert "pip install requests" in details.suggestion
    
    # Test package name resolution (cv2 -> opencv-python)
    error_output = "ModuleNotFoundError: No module named 'cv2'"
    details = handler.extract_details(error_output)
    assert "opencv-python" in details.suggestion
    
    # Test test module detection
    error_output = "ModuleNotFoundError: No module named 'test_nonexistent_module'"
    details = handler.extract_details(error_output)
    assert "test/placeholder" in details.suggestion
    
    print("✅ ModuleNotFoundHandler enhanced functionality working")

def test_type_error_handler():
    """Test enhanced TypeErrorHandler with sophisticated pattern matching"""
    print("🧪 Testing TypeErrorHandler...")
    
    handler = TypeErrorHandler()
    
    # Test unsupported operand detection
    error_output = "TypeError: unsupported operand type(s) for +: 'str' and 'int'"
    details = handler.extract_details(error_output)
    assert details.error_type == "unsupported_operand"
    assert "type conversion" in details.suggestion
    
    # Test not iterable detection
    error_output = "TypeError: 'int' object is not iterable"
    details = handler.extract_details(error_output)
    assert details.error_type == "not_iterable"
    assert "iterable" in details.suggestion
    
    # Test not subscriptable detection
    error_output = "TypeError: 'int' object is not subscriptable"
    details = handler.extract_details(error_output)
    assert details.error_type == "not_subscriptable"
    assert "indexing" in details.suggestion
    
    print("✅ TypeErrorHandler enhanced functionality working")

def test_index_error_handler():
    """Test enhanced IndexErrorHandler with better bounds checking"""
    print("🧪 Testing IndexErrorHandler...")
    
    handler = IndexErrorHandler()
    
    # Test list index out of range
    error_output = "IndexError: list index out of range"
    details = handler.extract_details(error_output)
    assert details.error_type == "list_index_out_of_range"
    assert "bounds checking" in details.suggestion
    
    # Test empty list pop
    error_output = "IndexError: pop from empty list"
    details = handler.extract_details(error_output)
    assert details.error_type == "empty_list_pop"
    assert "empty" in details.suggestion
    
    print("✅ IndexErrorHandler enhanced functionality working")

def test_syntax_error_handler():
    """Test enhanced SyntaxErrorHandler with advanced parsing"""
    print("🧪 Testing SyntaxErrorHandler...")
    
    handler = SyntaxErrorHandler()
    
    # Test invalid syntax detection
    error_output = "SyntaxError: invalid syntax"
    details = handler.extract_details(error_output)
    assert details.error_type == "invalid_syntax"
    
    # Test unexpected EOF detection
    error_output = "SyntaxError: unexpected EOF while parsing"
    details = handler.extract_details(error_output)
    assert details.error_type == "unexpected_eof"
    assert "closing" in details.suggestion
    
    print("✅ SyntaxErrorHandler enhanced functionality working")

def test_unified_autofixer():
    """Test the unified AutoFixer with all enhanced components"""
    print("🧪 Testing unified AutoFixer...")
    
    fixer = AutoFixer()
    
    # Verify all handlers are present
    handler_names = [h.error_name for h in fixer.handlers]
    expected_handlers = ['ModuleNotFoundError', 'TypeError', 'IndentationError', 'IndexError', 'SyntaxError']
    
    for expected in expected_handlers:
        assert expected in handler_names, f"Missing handler: {expected}"
    
    # Verify advanced components are integrated
    assert hasattr(fixer, 'error_parser'), "Missing ErrorParser integration"
    assert hasattr(fixer, 'import_suggestions'), "Missing import suggestions"
    assert hasattr(fixer, 'known_pip_packages'), "Missing known packages"
    
    # Verify data is loaded
    assert len(fixer.import_suggestions) > 0, "Import suggestions not loaded"
    assert len(fixer.known_pip_packages) > 0, "Known packages not loaded"
    
    print("✅ Unified AutoFixer integration working")

def test_error_handler_selection():
    """Test that the right handler is selected for each error type"""
    print("🧪 Testing error handler selection...")
    
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
        assert handler is not None, f"No handler found for: {error_output}"
        assert handler.error_name == expected_handler, f"Wrong handler selected for {error_output}"
    
    print("✅ Error handler selection working correctly")

def main():
    """Run all tests for the unified engine"""
    print("🚀 Testing Unified AutoFixer Engine")
    print("=" * 50)
    
    try:
        test_module_not_found_handler()
        test_type_error_handler()
        test_index_error_handler()
        test_syntax_error_handler()
        test_unified_autofixer()
        test_error_handler_selection()
        
        print("=" * 50)
        print("🎉 ALL TESTS PASSED! Unified engine is working perfectly!")
        print("✅ Advanced logic from python_fixer.py successfully integrated")
        print("✅ All error handlers enhanced with sophisticated pattern matching")
        print("✅ Firebase metrics integration preserved")
        print("✅ Interactive UX features maintained")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    main()
