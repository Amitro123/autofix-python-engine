#!/usr/bin/env python3
"""
Transaction-based error fixing demonstration
"""

from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from error_parser import ErrorParser
from autofix_cli_interactive import AutoFixer, TypeErrorHandler, SyntaxErrorHandler

def demo_transaction_fix():
    """Demonstrate transaction-based error fixing"""
    
    # Create a test file with errors
    test_file = Path("temp_test_script.py")
    test_content = '''#!/usr/bin/env python3
# Test script with intentional errors

def test_function():
    # This will cause TypeError: string + int
    result = "Hello" + 123
    return result

if __name__ == "__main__":
    test_function()
'''
    
    # Write test file
    with open(test_file, 'w') as f:
        f.write(test_content)
    
    print("=== Transaction-based Error Fixing Demo ===")
    print(f"Created test file: {test_file}")
    print(f"Original content:\n{test_content}")
    
    # Initialize error parser
    parser = ErrorParser()
    
    # Demo 1: Successful fix with transaction
    print("\n--- Demo 1: Successful Fix with Transaction ---")
    
    # Mock error details for TypeError
    error_details = {
        'error_type': 'unsupported_operand',
        'line_number': 6,
        'suggestion': 'Fix type mismatch in operation (e.g., string + int)'
    }
    
    try:
        success = parser.apply_fix_with_transaction(
            str(test_file), 
            fix_type_error, 
            error_details
        )
        
        if success:
            print("[SUCCESS] Fix applied successfully!")
            print("Fixed content:")
            print(test_file.read_text())
        else:
            print("[FAILED] Fix failed")
            
    except Exception as e:
        print(f"[ERROR] Error during fix: {e}")
    
    # Demo 2: Using SafeFixContext for multiple fixes
    print("\n--- Demo 2: Safe Fix Context for Multiple Operations ---")
    
    # Reset test file with multiple errors
    multi_error_content = '''#!/usr/bin/env python3
# Test script with multiple errors

def test_function():
    # TypeError: string + int
    result1 = "Hello" + 123
    
    # AttributeError: str has no attribute append
    text = "world"
    text.append("!")
    
    return result1, text

if __name__ == "__main__":
    test_function()
'''
    
    with open(test_file, 'w') as f:
        f.write(multi_error_content)
    
    print(f"Reset test file with multiple errors:\n{multi_error_content}")
    
    try:
        with parser.create_safe_fix_context(str(test_file)) as ctx:
            # Apply multiple fixes
            type_error_details = {
                'error_type': 'unsupported_operand',
                'line_number': 6,
                'suggestion': 'Fix type mismatch in operation'
            }
            
            attr_error_details = {
                'error_type': 'missing_attribute',
                'object_name': 'str',
                'attribute_name': 'append',
                'line_number': 10,
                'suggestion': 'String objects don\'t have append method'
            }
            
            # Apply fixes within transaction
            ctx.apply_fix(fix_type_error, type_error_details)
            ctx.apply_fix(fix_attribute_error, attr_error_details)
            
        print("[SUCCESS] Multiple fixes applied successfully!")
        print("Final content:")
        print(test_file.read_text())
        
    except Exception as e:
        print(f"[ERROR] Error during multi-fix: {e}")
        print("File should be restored to original state")
        print("Current content:")
        print(test_file.read_text())
    
    # Demo 3: Failed fix with automatic rollback
    print("\n--- Demo 3: Failed Fix with Automatic Rollback ---")
    
    # Create a scenario that will fail
    def failing_fix_function(script_path, error_details):
        """A fix function that always fails"""
        print("Attempting fix that will fail...")
        # Simulate some file modification
        with open(script_path, 'a') as f:
            f.write("\n# This line should be rolled back")
        # Then fail
        raise ValueError("Simulated fix failure!")
    
    original_content = test_file.read_text()
    print(f"Content before failed fix attempt:\n{original_content}")
    
    try:
        success = parser.apply_fix_with_transaction(
            str(test_file),
            failing_fix_function,
            {}
        )
        print(f"Fix result: {success}")
        
    except Exception as e:
        print(f"Expected error caught: {e}")
    
    restored_content = test_file.read_text()
    print(f"Content after rollback:\n{restored_content}")
    
    if original_content == restored_content:
        print("[SUCCESS] Rollback successful - file restored to original state!")
    else:
        print("[FAILED] Rollback failed - file content differs!")
    
    # Cleanup
    if test_file.exists():
        os.remove(test_file)
        print(f"\nCleaned up test file: {test_file}")

if __name__ == "__main__":
    demo_transaction_fix()
