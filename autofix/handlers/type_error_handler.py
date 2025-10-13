from ..core.base_handler import ErrorHandler
from ..constants import ErrorType
from typing import Tuple, Dict, List, Optional
import re
import logging

logger = logging.getLogger(__name__)

class TypeErrorHandler(ErrorHandler):
    """Handler for TypeError - provides suggestions only (PARTIAL)"""
    
    def __init__(self):
        super().__init__()
        
    def can_handle(self, error_output: str) -> bool:
        return "TypeError" in error_output
        
    def analyze_error(self, error_output: str, file_path: str = None) -> Tuple[str, str, Dict]:
        """Analyze TypeError and provide detailed suggestions"""
        
        # Extract line number
        line_matches = re.findall(r'line (\d+)', error_output)
        line_number = int(line_matches[0]) if line_matches else None
        
        # Analyze specific TypeError pattern
        error_type, suggestion = self._analyze_type_error(error_output)
        
        details = {
            "error_output": error_output,
            "line_number": line_number,
            "fix_type": error_type,
            "suggestions": self._get_suggestions(error_type, error_output),
            "file_path": file_path
        }
        
        return error_type, suggestion, details

    def _analyze_type_error(self, error_output: str) -> Tuple[str, str]:
        """Advanced analysis of TypeError patterns"""
        
        # String concatenation with numbers
        if "can only concatenate str" in error_output or "unsupported operand" in error_output:
            return "string_concatenation", "Convert number to string: str(number) or use f-string"
        
        # String to number conversion errors
        if "invalid literal for int()" in error_output:
            return "string_concatenation", "Cannot convert string to integer - check input format or use try/except"
        
        if "could not convert string to float" in error_output:
            return "string_concatenation", "Cannot convert string to float - check input format or use try/except"
        
        # Function argument issues
        if "takes" in error_output and "positional argument" in error_output:
            return "argument_count", "Fix function argument count mismatch"
        
        if "missing" in error_output and "required positional argument" in error_output:
            return "missing_argument", "Add missing required function arguments"
        
        # Object attribute/method issues
        if "object has no attribute" in error_output:
            return "missing_attribute", "Check object type and available attributes/methods"
        
        # Iteration issues
        if "not iterable" in error_output:
            return "not_iterable", "Object cannot be iterated - convert to list/tuple"
        
        # Subscript issues
        if "not subscriptable" in error_output:
            return "not_subscriptable", "Object doesn't support indexing - check type"
        
        # Callable issues
        if "not callable" in error_output:
            return "not_callable", "Object is not a function - remove parentheses"
        
        return "general_type", "Fix type-related error"

    def _get_suggestions(self, error_type: str, error_output: str) -> List[str]:
        """Get specific fix suggestions based on error type"""
        
        if error_type == "string_concatenation":
            return [
                "result = 'hello' + str(5)",
                "result = f'hello{5}'",
                "result = 'hello' + '{}'.format(5)"
            ]
        
        elif error_type == "argument_count":
            return [
                "Check function definition and call",
                "Add missing arguments",
                "Remove extra arguments"
            ]
        
        elif error_type == "not_iterable":
            return [
                "Convert to list: list(variable)",
                "Check if variable is None",
                "Use list comprehension: [item for item in variable]"
            ]
            
        elif error_type == "not_subscriptable":
            return [
                "Check if variable is a list/dict/tuple",
                "Use getattr() for object attributes",
                "Convert to indexable type"
            ]
            
        return ["Review variable types and operations"]

    def apply_fix(self, error_type: str, file_path: str, details: Dict) -> bool:
        """TypeErrorHandler only provides suggestions (PARTIAL result)"""
        
        print(f"\nTypeError detected in {file_path}")
        print(f"Error type: {error_type}")
        print(f"Line: {details.get('line_number', 'Unknown')}")
        print("\nSuggested fixes:")
        
        suggestions = details.get("suggestions", [])
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
            
        print(f"\nSuggestion: {details.get('suggestion', 'Review code')}")
        
        # Return False - we don't auto-fix TypeErrors, only suggest
        return False
