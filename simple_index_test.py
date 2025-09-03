#!/usr/bin/env python3
"""
Simple IndexError test script
"""

def main():
    print("Testing IndexError...")
    
    # This will cause IndexError: list index out of range
    my_list = [1, 2, 3]
    value = my_list[5] if len(my_list) > 5 else None
    print(f"Value: {value}")

if __name__ == "__main__":
    main()
