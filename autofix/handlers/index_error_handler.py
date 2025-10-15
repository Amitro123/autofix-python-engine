from autofix.core.base_handler import ErrorHandler
from typing import Tuple, Dict, List
import re

class IndexErrorHandler(ErrorHandler):
    """Handler for IndexError - provides suggestions only (PARTIAL)"""
    
    def can_handle(self, error_output: str) -> bool:
        return "IndexError" in error_output
        
    def analyze_error(self, error_output: str, file_path: str = None) -> Tuple[str, str, Dict]:
        line_matches = re.findall(r'line (\d+)', error_output)
        line_number = int(line_matches[0]) if line_matches else None
        
        # Use advanced analysis
        error_subtype, suggestion = self._analyze_index_error(error_output)
        
        details = {
            "error_output": error_output,
            "line_number": line_number,
            "error_subtype": error_subtype,
            "suggestions": self._get_suggestions(error_subtype),
            "file_path": file_path
        }
        
        return "index_error", suggestion, details
    
    def _analyze_index_error(self, error_output: str) -> Tuple[str, str]:
        """Advanced analysis of IndexError patterns"""
        if "list index out of range" in error_output:
            return "list_index_out_of_range", "Add bounds checking for list access"
        elif "string index out of range" in error_output:
            return "string_index_out_of_range", "Add bounds checking for string access"
        elif "tuple index out of range" in error_output:
            return "tuple_index_out_of_range", "Add bounds checking for tuple access"
        elif "pop from empty list" in error_output:
            return "empty_list_pop", "Check if list is not empty before pop()"
        else:
            return "general_index", "Add bounds checking for sequence access"
    
    def _get_suggestions(self, error_subtype: str) -> List[str]:
        """Get specific suggestions based on error subtype"""
        suggestions_map = {
            "list_index_out_of_range": [
                "Check list bounds: if index < len(list)",
                "Use try-except to handle IndexError",
                "Verify index is within valid range",
                "Consider using conditional access"
            ],
            "empty_list_pop": [
                "Check if list is not empty: if list:",
                "Use: item = list.pop() if list else None",
                "Add validation before pop()",
                "Consider using collections.deque"
            ],
            "string_index_out_of_range": [
                "Check string length before access",
                "Use slicing for safety: string[:index]",
                "Add bounds validation",
                "Handle empty strings"
            ],
            "tuple_index_out_of_range": [
                "Verify tuple length",
                "Use try-except for safe access",
                "Check index against len(tuple)",
                "Consider tuple unpacking"
            ]
        }
        
        return suggestions_map.get(error_subtype, [
            "Add bounds checking for sequence access",
            "Use try-except to handle IndexError gracefully",
            "Verify index is valid before access",
            "Check sequence length with len()"
        ])
        
    def apply_fix(self, error_type: str, file_path: str, details: Dict) -> bool:
        """Provide suggestions only - no auto-fix for IndexError"""
        print(f"\nIndexError detected in {file_path}")
        
        error_subtype = details.get('error_subtype', 'general_index')
        if error_subtype != 'general_index':
            print(f"Type: {error_subtype.replace('_', ' ')}")
        
        if details.get('line_number'):
            print(f"Line: {details['line_number']}")
        
        print("\nSuggestions:")
        for i, suggestion in enumerate(details.get('suggestions', []), 1):
            print(f"  {i}. {suggestion}")
        
        print("\nIndexError requires manual review - PARTIAL result")
        return False  # PARTIAL - suggestions only, no auto-fix
