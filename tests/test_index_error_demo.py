#!/usr/bin/env python3
"""
Test script with intentional IndexError for AutoFix demonstration
"""

def main():
    print("Testing IndexError handling...")
    
    # Test 1: List index out of range
    my_list = [1, 2, 3]
    print(f"List: {my_list}")
    
    # This will cause IndexError: list index out of range
    value = my_list[5]
    print(f"Value at index 5: {value}")
    
    # Test 2: String index out of range
    my_string = "Hello"
    print(f"String: {my_string}")
    
    # This will also cause IndexError: string index out of range
    char = my_string[10]
    print(f"Character at index 10: {char}")
    
    print("Demo completed!")

if __name__ == "__main__":
    main()
