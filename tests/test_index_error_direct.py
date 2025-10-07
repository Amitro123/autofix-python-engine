#!/usr/bin/env python3
"""
Direct test of IndexError fixing without Firebase dependency
"""

from autofix.python_fixer import PythonFixer
from autofix.core.error_parser import ErrorParser
import tempfile
import os

def test_index_error_fixing():
    """Test IndexError detection and fixing"""
    
    # Create a temporary script with IndexError
    test_script_content = '''#!/usr/bin/env python3
"""Test script with IndexError"""

def main():
    print("Testing IndexError...")
    
    # This will cause IndexError: list index out of range
    my_list = [1, 2, 3]
    value = my_list[5]
    print(f"Value: {value}")

if __name__ == "__main__":
    main()
'''
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_script_content)
        temp_script = f.name
    
    try:
        print(f"Created test script: {temp_script}")
        print("Original content:")
        print("-" * 40)
        print(test_script_content)
        print("-" * 40)
        
        # Initialize fixer and parser
        fixer = PythonFixer()
        parser = ErrorParser()
        
        print("\n1. Running script to capture IndexError...")
        success = fixer.run_script_with_fixes(temp_script)
        
        if success:
            print("✅ Script ran successfully after fixes!")
            
            # Show the fixed content
            print("\nFixed content:")
            print("-" * 40)
            with open(temp_script, 'r') as f:
                print(f.read())
            print("-" * 40)
        else:
            print("❌ Script still has errors after fix attempt")
            
    except Exception as e:
        print(f"Error during test: {e}")
        
    finally:
        # Clean up
        if os.path.exists(temp_script):
            os.unlink(temp_script)
            print(f"Cleaned up: {temp_script}")

if __name__ == "__main__":
    test_index_error_fixing()
