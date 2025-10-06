#!/usr/bin/env python3
"""Test case for missing package that should trigger pip installation."""

print("Testing missing package installation...")

# This will cause ModuleNotFoundError that AutoFix should fix by installing opencv-python
import cv2

print("OpenCV imported successfully!")
print(f"OpenCV version: {cv2.__version__}")