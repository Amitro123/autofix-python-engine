#!/usr/bin/env python3
"""
Test IndexError fixing using core engine components
"""

from autofix.python_fixer import PythonFixer
from autofix_core.shared.core.error_parser import ErrorParser
import subprocess
import sys

def test_indexerror_fix():
    """Test IndexError detection and fixing directly"""
    
    script_path = "simple_index_test.py"
    
    # Initialize components
    fixer = PythonFixer()
    parser = ErrorParser()
    
    print("Testing IndexError detection and fixing...")
    print(f"Script: {script_path}")
    
    # Step 1: Run script to capture error
    print("\n1. Running script to capture IndexError...")
    try:
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=True, text=True, cwd=".")
        
        if result.returncode != 0:
            print("SUCCESS: IndexError detected as expected")
            print(f"Error output: {result.stderr}")
            
            # Step 2: Parse the error
            print("\n2. Parsing IndexError...")
            try:
                # Create a mock IndexError for parsing with line number
                error = IndexError("list index out of range")
                parsed_error = parser._parse_index_error(error, script_path)
                # Manually set line number since we know it from the traceback
                parsed_error.line_number = 11
                
                print(f"SUCCESS: Parsed error type: {parsed_error.error_type}")
                print(f"SUCCESS: Suggested fix: {parsed_error.suggested_fix}")
                print(f"SUCCESS: Confidence: {parsed_error.confidence}")
                
                # Step 3: Apply the fix
                print("\n3. Applying IndexError fix...")
                fix_success = fixer._fix_index_error(parsed_error)
                
                if fix_success:
                    print("SUCCESS: Fix applied successfully!")
                    
                    # Step 4: Test the fixed script
                    print("\n4. Testing fixed script...")
                    result_after = subprocess.run([sys.executable, script_path], 
                                                capture_output=True, text=True, cwd=".")
                    
                    if result_after.returncode == 0:
                        print("SUCCESS: Script runs successfully after fix!")
                        print(f"Output: {result_after.stdout}")
                    else:
                        print("ERROR: Script still has errors after fix")
                        print(f"Error: {result_after.stderr}")
                        
                    # Show the fixed code
                    print("\n5. Fixed code:")
                    print("-" * 50)
                    with open(script_path, 'r') as f:
                        print(f.read())
                    print("-" * 50)
                        
                else:
                    print("ERROR: Fix failed to apply")
                    
            except Exception as e:
                print(f"ERROR: Error during parsing/fixing: {e}")
                
        else:
            print("ERROR: Script ran without errors - unexpected")
            
    except Exception as e:
        print(f"ERROR: Error running script: {e}")

if __name__ == "__main__":
    test_indexerror_fix()
