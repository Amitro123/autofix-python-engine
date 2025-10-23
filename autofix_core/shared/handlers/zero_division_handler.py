from autofix_core.shared.core.base_handler import ErrorHandler
from typing import Tuple, Dict, List
import re

class ZeroDivisionHandler(ErrorHandler):
    """Handler for ZeroDivisionError - provides suggestions only (PARTIAL)"""
    
    def can_handle(self, error_output: str) -> bool:
        return "ZeroDivisionError" in error_output
        
    def analyze_error(self, error_output: str, file_path: str = None) -> Tuple[str, str, Dict]:
        line_matches = re.findall(r'line (\d+)', error_output)
        line_number = int(line_matches[0]) if line_matches else None
        
        details = {
            "error_output": error_output,
            "line_number": line_number,
            "suggestions": [
                "Add validation: if divisor != 0",
                "Check denominator before division",
                "Use try-except to handle division errors",
                "Ensure divisor is never zero"
            ],
            "file_path": file_path
        }
        
        return "zero_division", "Division by zero", details
        
    def apply_fix(self, error_type: str, file_path: str, details: Dict) -> bool:
        print(f"\nZeroDivisionError detected in {file_path}")
        if details.get('line_number'):
            print(f"Line: {details['line_number']}")
        
        print("\nSuggestions:")
        for i, suggestion in enumerate(details.get('suggestions', []), 1):
            print(f"  {i}. {suggestion}")
        
        print("\nZeroDivisionError requires manual review - PARTIAL result")
        return False
