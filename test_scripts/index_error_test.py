#!/usr/bin/env python3
"""
Test script for IndexError - should trigger enhanced handler
"""

def main():
    # This will cause IndexError: list index out of range
    my_list = [1, 2, 3]
    print(my_list[5])
    
    # This will cause IndexError: string index out of range
    my_string = "hello"
    print(my_string[10])
    
    # This will cause IndexError: pop from empty list
    empty_list = []
    empty_list.pop()

if __name__ == "__main__":
    main()
