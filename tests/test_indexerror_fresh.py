#!/usr/bin/env python3
"""
Test script with IndexError for testing Firebase metrics
"""

def main():
    print("Testing IndexError...")
    
    # This will cause IndexError: list index out of range
    my_list = [1, 2, 3]
    value = my_list[5]  # This line will fail
    print(f"Value: {value}")

if __name__ == "__main__":
    main()
