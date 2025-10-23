from autofix_core.shared.core.base_handler import ErrorHandler
from typing import Tuple, Dict
import re


class ValueErrorHandler(ErrorHandler):
    """Handler for ValueError - type conversion errors"""
    
    def can_handle(self, error_output: str) -> bool:
        """Check if this handler can handle the error"""
        return "ValueError" in error_output
    
    def analyze_error(self, error_output: str, file_path: str = None) -> Tuple[str, str, Dict]:
        """Analyze ValueError and provide context-specific suggestions"""
        
        # Extract line number
        line_matches = re.findall(r'line (\d+)', error_output)
        line_number = int(line_matches[0]) if line_matches else None
        
        # Determine specific ValueError type
        error_description = "Invalid value conversion"
        conversion_type = None
        invalid_value = "unknown"
        
        # Check for int() conversion error
        if "invalid literal for int()" in error_output:
            error_description = "Cannot convert string to integer"
            conversion_type = "int"
            value_match = re.search(r"'([^']+)'", error_output)
            invalid_value = value_match.group(1) if value_match else "value"
            
        # Check for float() conversion error
        elif "could not convert string to float" in error_output:
            error_description = "Cannot convert string to float"
            conversion_type = "float"
            value_match = re.search(r"'([^']+)'", error_output)
            invalid_value = value_match.group(1) if value_match else "value"
            
        # Check for other common ValueError patterns
        elif "substring not found" in error_output:
            error_description = "Substring not found in string"
            conversion_type = "substring"
            
        elif "empty range" in error_output:
            error_description = "Empty range for random choice"
            conversion_type = "range"
        
        details = {
            "error_output": error_output,
            "line_number": line_number,
            "conversion_type": conversion_type,
            "invalid_value": invalid_value,
            "suggestions": self._generate_suggestions(conversion_type, invalid_value),
            "file_path": file_path,
            "example_fix": self._generate_example_fix(conversion_type, invalid_value)
        }
        
        return "value_error", error_description, details
    
    def _generate_suggestions(self, conversion_type: str, invalid_value: str) -> list:
        """Generate context-specific suggestions based on error type"""
        
        if conversion_type == "int":
            return [
                "Validate input before conversion: if value.isdigit()",
                "Use try/except to handle conversion errors",
                "Provide default value on error",
                "Strip whitespace: int(value.strip())",
                f"Invalid value: '{invalid_value}' is not a valid integer"
            ]
            
        elif conversion_type == "float":
            return [
                "Validate input before float conversion",
                "Use try/except to handle conversion errors",
                "Check for valid float format (allow decimal point)",
                f"Invalid value: '{invalid_value}' is not a valid float",
                "Consider: float(value.strip())"
            ]
            
        elif conversion_type == "substring":
            return [
                "Check if substring exists before using .index()",
                "Use .find() instead of .index() (returns -1 if not found)",
                "Use 'in' operator to check: if substring in string",
                "Add substring existence validation"
            ]
            
        elif conversion_type == "range":
            return [
                "Check if list/range is not empty before random.choice()",
                "Add validation: if len(items) > 0",
                "Provide default value for empty collections"
            ]
            
        else:
            return [
                "Validate input data before processing",
                "Use try/except to handle value errors",
                "Check data format and constraints",
                "Add input validation logic",
                "Review the value being processed"
            ]
    
    def _generate_example_fix(self, conversion_type: str, invalid_value: str) -> str:
        """Generate example fix based on conversion type"""
        
        if conversion_type == "int":
            return f"""
💡 Example Fix for int() conversion:

# Before (crashes on invalid input):
number = int(user_input)  # ❌ Crashes if user_input = "{invalid_value}"

# Fix Option 1 - Validation:
if user_input.isdigit():
    number = int(user_input)
else:
    print(f"Invalid input: {{user_input}}")
    number = 0  # default value

# Fix Option 2 - Try/Except (RECOMMENDED):
try:
    number = int(user_input)
except ValueError:
    print(f"Cannot convert '{{user_input}}' to integer")
    number = 0  # default value

# Fix Option 3 - One-liner with default:
number = int(user_input) if user_input.isdigit() else 0

# Fix Option 4 - Strip whitespace:
try:
    number = int(user_input.strip())
except ValueError:
    number = 0
"""
            
        elif conversion_type == "float":
            return f"""
💡 Example Fix for float() conversion:

# Before (crashes on invalid input):
number = float(user_input)  # ❌ Crashes if user_input = "{invalid_value}"

# Fix Option 1 - Try/Except (RECOMMENDED):
try:
    number = float(user_input)
except ValueError:
    print(f"Cannot convert '{{user_input}}' to float")
    number = 0.0  # default value

# Fix Option 2 - With whitespace handling:
try:
    number = float(user_input.strip())
except ValueError:
    number = 0.0

# Fix Option 3 - More robust:
def safe_float(value, default=0.0):
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        return default

number = safe_float(user_input)
"""
            
        elif conversion_type == "substring":
            return """
💡 Example Fix for substring operations:

# Before (crashes if substring not found):
index = text.index("substring")  # ❌ Raises ValueError

# Fix Option 1 - Use find() instead:
index = text.find("substring")  # Returns -1 if not found
if index != -1:
    # substring found
    pass

# Fix Option 2 - Check before using:
if "substring" in text:
    index = text.index("substring")
else:
    index = -1

# Fix Option 3 - Try/Except:
try:
    index = text.index("substring")
except ValueError:
    index = -1
"""
            
        elif conversion_type == "range":
            return """
💡 Example Fix for empty range/list:

# Before (crashes on empty list):
import random
choice = random.choice(items)  # ❌ ValueError if items is empty

# Fix Option 1 - Check before using:
if len(items) > 0:
    choice = random.choice(items)
else:
    choice = None  # or default value

# Fix Option 2 - Try/Except:
try:
    choice = random.choice(items)
except ValueError:
    choice = None

# Fix Option 3 - One-liner:
choice = random.choice(items) if items else None
"""
            
        else:
            return """
💡 General ValueError Fix:

# Use try/except to handle value errors:
try:
    # Your code that might raise ValueError
    result = some_function(data)
except ValueError as e:
    print(f"Value error: {e}")
    result = default_value  # provide fallback

# Or validate input beforehand:
if is_valid(data):
    result = process(data)
else:
    result = default_value
"""
    
    def apply_fix(self, error_type: str, file_path: str, details: Dict) -> bool:
        """Provide suggestions - cannot auto-fix value conversion issues"""
        
        print(f"\n{'='*60}")
        print(f"ValueError detected in {file_path}")
        print(f"{'='*60}")
        
        if details.get('line_number'):
            print(f"Line: {details['line_number']}")
        
        if details.get('conversion_type'):
            print(f"Type: {details['conversion_type']} conversion")
        
        if details.get('invalid_value') and details.get('invalid_value') != "unknown":
            print(f"Invalid value: '{details['invalid_value']}'")
        
        print("\nSuggestions:")
        for i, suggestion in enumerate(details.get('suggestions', []), 1):
            print(f"  {i}. {suggestion}")
        
        if 'example_fix' in details:
            print(details['example_fix'])
        
        print("\nValueError requires manual review - PARTIAL result")
        print(f"{'='*60}\n")
        return False
