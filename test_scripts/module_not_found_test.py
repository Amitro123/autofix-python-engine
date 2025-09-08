#!/usr/bin/env python3
"""
Test script for ModuleNotFoundError - should trigger enhanced handler
"""

import requests  # This will cause ModuleNotFoundError if not installed
import cv2       # This should resolve to opencv-python

def main():
    response = requests.get("https://httpbin.org/json")
    print(f"Status: {response.status_code}")
    
    # Use cv2 functionality
    print("OpenCV version:", cv2.__version__)

if __name__ == "__main__":
    main()
