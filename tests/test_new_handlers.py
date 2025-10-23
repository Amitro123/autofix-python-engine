"""
Quick tests for new error handlers
"""
import pytest
from autofix_core.shared.handlers.file_not_found_handler import FileNotFoundHandler
from autofix_core.shared.handlers.value_error_handler import ValueErrorHandler


def test_file_not_found_handler_can_handle():
    """Test FileNotFoundError detection"""
    handler = FileNotFoundHandler()
    
    # Test with typical FileNotFoundError
    error1 = "FileNotFoundError: [Errno 2] No such file or directory: 'data.txt'"
    assert handler.can_handle(error1)
    
    # Test with alternative format
    error2 = "No such file or directory: 'missing.csv'"
    assert handler.can_handle(error2)
    
    # Should not handle other errors
    error3 = "ValueError: invalid literal"
    assert not handler.can_handle(error3)
    
    print("✅ FileNotFoundHandler.can_handle() works!")


def test_file_not_found_handler_analyze():
    """Test FileNotFoundError analysis"""
    handler = FileNotFoundHandler()
    
    error_output = "FileNotFoundError: [Errno 2] No such file or directory: 'data.txt'"
    error_type, description, details = handler.analyze_error(error_output, "test.py")
    
    assert error_type == "file_not_found"
    assert "data.txt" in description
    assert details['missing_file'] == 'data.txt'
    assert len(details['suggestions']) > 0
    assert 'example_fix' in details
    
    print("✅ FileNotFoundHandler.analyze_error() works!")


def test_value_error_handler_can_handle():
    """Test ValueError detection"""
    handler = ValueErrorHandler()
    
    # Test with ValueError
    error1 = "ValueError: invalid literal for int() with base 10: 'abc'"
    assert handler.can_handle(error1)
    
    # Test with float conversion
    error2 = "ValueError: could not convert string to float: 'xyz'"
    assert handler.can_handle(error2)
    
    # Should not handle other errors
    error3 = "FileNotFoundError: missing file"
    assert not handler.can_handle(error3)
    
    print("✅ ValueErrorHandler.can_handle() works!")


def test_value_error_handler_analyze_int():
    """Test ValueError analysis for int() conversion"""
    handler = ValueErrorHandler()
    
    error_output = "ValueError: invalid literal for int() with base 10: 'abc'"
    error_type, description, details = handler.analyze_error(error_output, "test.py")
    
    assert error_type == "value_error"
    assert "integer" in description.lower()
    assert details['conversion_type'] == 'int'
    assert details['invalid_value'] == 'abc'
    assert len(details['suggestions']) > 0
    assert 'example_fix' in details
    
    print("✅ ValueErrorHandler.analyze_error() works for int!")


def test_value_error_handler_analyze_float():
    """Test ValueError analysis for float() conversion"""
    handler = ValueErrorHandler()
    
    error_output = "ValueError: could not convert string to float: 'xyz'"
    error_type, description, details = handler.analyze_error(error_output, "test.py")
    
    assert error_type == "value_error"
    assert "float" in description.lower()
    assert details['conversion_type'] == 'float'
    assert details['invalid_value'] == 'xyz'
    
    print("✅ ValueErrorHandler.analyze_error() works for float!")


def test_handlers_return_false():
    """Test that handlers return False (manual fix required)"""
    file_handler = FileNotFoundHandler()
    value_handler = ValueErrorHandler()
    
    # Both should return False (cannot auto-fix)
    result1 = file_handler.apply_fix("file_not_found", "test.py", {"missing_file": "data.txt", "suggestions": []})
    result2 = value_handler.apply_fix("value_error", "test.py", {"conversion_type": "int", "suggestions": []})
    
    assert result1 == False
    assert result2 == False
    
    print("✅ Handlers correctly return False (manual fix required)!")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Testing New Error Handlers")
    print("="*60 + "\n")
    
    # Run all tests
    test_file_not_found_handler_can_handle()
    test_file_not_found_handler_analyze()
    test_value_error_handler_can_handle()
    test_value_error_handler_analyze_int()
    test_value_error_handler_analyze_float()
    test_handlers_return_false()
    
    print("\n" + "="*60)
    print("🎉 All tests passed!")
    print("="*60 + "\n")
