#!/usr/bin/env python3
"""
Test script with intentional indentation errors
"""

def main():
    print("Testing indentation...")
    
    # This will cause IndentationError: expected an indented block
    if True:
        print("This line has no indentation!")
    
    print("Demo completed!")

if __name__ == "__main__":
    main()
