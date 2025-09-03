#!/usr/bin/env python3
"""
Test script with intentional TypeError
"""

def main():
    print("Testing TypeError handling...")
    
    # This will cause TypeError: unsupported operand type(s) for +: 'str' and 'int'
    name = "Hello"
    number = 123
    result = name + number
    
    print(f"Result: {result}")
    print("Demo completed!")

if __name__ == "__main__":
    main()
