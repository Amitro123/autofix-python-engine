#!/usr/bin/env python3
from time import sleep
from datetime import datetime
import random
"""
Test script with missing import to demonstrate AutoFix capability
"""

def main():
    print("Testing missing import fix...")
    
    # This will cause NameError - missing import for sleep
    sleep(2)
    
    # This will cause NameError - missing import for datetime
    now = datetime.now()
    print(f"Current time: {now}")
    
    # This will cause NameError - missing import for random
    number = random.randint(1, 10)
    print(f"Random number: {number}")
    
    print("Demo completed!")

if __name__ == "__main__":
    main()
