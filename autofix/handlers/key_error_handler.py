from autofix.core.base_handler import BaseHandler
from typing import Tuple, Dict, List
import re

class KeyErrorHandler(BaseHandler):
    """Handler for KeyError - provides suggestions only (PARTIAL)"""
    
    def can_handle(self, error_output: str) -> bool:
        return "KeyError" in error_output
        
    def analyze_error(self, error_output: str, file_path: str = None) -> Tuple[str, str, Dict]:
        line_matches = re.findall(r'line (\d+)', error_output)
        line_number = int(line_matches[0]) if line_matches else None
        
        details = {
            "error_output": error_output,
            "line_number": line_number,
            "suggestions": [
                "Check if key exists: if 'key' in dict",
                "Use dict.get('key', default_value)",
                "Verify dictionary structure",
                "Add key existence validation"
            ],
            "file_path": file_path
        }
        
        return "key_error", "Dictionary key not found", details
        
    def apply_fix(self, error_type: str, file_path: str, details: Dict) -> bool:
        print(f"\nKeyError detected in {file_path}")
        if details.get('line_number'):
            print(f"Line: {details['line_number']}")
        
        print("\nSuggestions:")
        for i, suggestion in enumerate(details.get('suggestions', []), 1):
            print(f"  {i}. {suggestion}")
        
        print("\nKeyError requires manual review - PARTIAL result")
        return False
