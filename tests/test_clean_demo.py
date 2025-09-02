#!/usr/bin/env python3
from time import sleep
"""
Clean test script for AutoFix functionality
"""

def main():
    print("Testing AutoFix...")
    
    # This should trigger NameError for missing import
    sleep(1)
    
    print("Demo completed!")

if __name__ == "__main__":
    main()