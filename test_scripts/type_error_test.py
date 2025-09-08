#!/usr/bin/env python3
"""
Test script for TypeError - should trigger enhanced handler
"""

def main():
    # This will cause TypeError: unsupported operand type(s) for +: 'str' and 'int'
    result = "Hello " + 42
    print(result)
    
    # This will cause TypeError: 'int' object is not iterable
    for item in 123:
        print(item)
    
    # This will cause TypeError: 'int' object is not subscriptable
    value = 456
    print(value[0])

if __name__ == "__main__":
    main()
