#!/usr/bin/env python3
"""
Test script for SyntaxError - should trigger enhanced handler
"""

def main()  # Missing colon - should be fixed by enhanced handler
    # This will cause SyntaxError: invalid syntax
    print("Hello World"
    
    # Broken keyword
    i f True:
        print("This should be fixed")
    
    # Missing closing parenthesis
    result = (1 + 2 + 3
    print(result)

if __name__ == "__main__":
    main()
