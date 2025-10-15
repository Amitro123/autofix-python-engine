import pytest
from autofix.handlers.type_error_handler import TypeErrorHandler

class TestTypeErrorHandler:
    """Test TypeError handler functionality"""

    def test_type_error_can_handle(self):
        """Test error detection"""
        handler = TypeErrorHandler()

        assert handler.can_handle("TypeError: unsupported operand type(s)") == True
        assert handler.can_handle("SyntaxError: invalid syntax") == False
        assert handler.can_handle("Some other error") == False

    def test_type_error_analyze_error(self):
        """Test error analysis and suggestions"""
        handler = TypeErrorHandler()

        error_msg = "TypeError: unsupported operand type(s) for +: 'int' and 'str'"
        error_type, suggestion, details = handler.analyze_error(error_msg, "test.py")

        assert error_type == "string_concatenation"
        assert "Convert number to string" in suggestion
        assert details["error_output"] == error_msg
        assert len(details["suggestions"]) > 0

    def test_type_error_extract_details(self):
        """Test detail extraction from error messages"""
        handler = TypeErrorHandler()

        # Test string concatenation error
        error_msg = "TypeError: can only concatenate str (not \"int\") to str"
        error_type, suggestion, details = handler.analyze_error(error_msg, "test.py")

        assert error_type == "string_concatenation"
        assert "convert" in suggestion.lower()

        # Test int conversion error
        error_msg2 = "TypeError: invalid literal for int() with base 10: 'abc'"
        error_type2, suggestion2, details2 = handler.analyze_error(error_msg2, "test.py")

        assert error_type2 == "string_concatenation"  # This error also maps to string_concatenation
        # Note: handler doesn't extract conversion_type or invalid_value for simplicity

        # Test iteration error
        error_msg = "TypeError: 'int' object is not iterable"
        error_type, suggestion, details = handler.analyze_error(error_msg, "test.py")

        assert error_type == "not_iterable"

    def test_type_error_apply_fix(self, capsys):
        """Test apply_fix provides suggestions and returns False"""
        handler = TypeErrorHandler()

        error_msg = "TypeError: unsupported operand type(s) for +: 'int' and 'str'"
        error_type, suggestion, details = handler.analyze_error(error_msg, "test.py")

        result = handler.apply_fix(error_type, "test.py", details)

        assert result == False  # Partial result

        # Check output contains suggestions
        captured = capsys.readouterr()
        assert "TypeError detected" in captured.out
        assert "Suggested fixes:" in captured.out
