#!/usr/bin/env python3
"""
Complex Test Script for AutoFix Engine
Contains multiple types of errors to test all handlers
"""

# ModuleNotFoundError - real packages
import requests  # Should work if installed
import numpy as np  # Should work if installed  
import nonexistent_module  # Should trigger autofix
import fake_test_module  # Should be identified as test module

# ModuleNotFoundError - package name variations
import cv2  # opencv-python
import PIL  # pillow
import sklearn  # scikit-learn

# ImportError - missing functions from modules
from os import nonexistent_function
from math import fake_function

# SyntaxError - missing colons
def calculate():  # Missing colon
    return 42

if True:  # Missing colon
    print("Hello")

for i in range(5):  # Missing colon
    print(i)

class TestClass:  # Missing colon
    pass

# SyntaxError - print statements (Python 2 vs 3)
print("This is Python 2 syntax")  # Should be print()

# NameError - undefined variables/functions
result = undefined_function(42)
value = undefined_variable + 10

# NameError - missing math functions
angle = sin(3.14)  # Missing from math import sin
radius = sqrt(25)  # Missing from math import sqrt

# IndexError - list access
my_list = [1, 2, 3]
item = my_list[10]  # Index out of bounds

empty_list = []
first_item = empty_list[0]  # Index error on empty list

# String indexing error
text = "hello"
char = text[100]  # String index out of range

# TypeError - type incompatibilities  
result = "Hello" + 42  # String + int
mixed = [1, 2, 3] + "string"  # List + string

# AttributeError - missing attributes
text = "hello"
result = text.nonexistent_method()

# IndentationError and mixed indentation
def poorly_indented():
    print("This line has wrong indentation")  # Should be indented
	print("This uses tab")  # Mixed tab/spaces
    print("This uses spaces")

# More complex scenarios
def complex_function():
    # Multiple errors in one function
    data = undefined_variable
    result = data[999]  # IndexError if data was defined
    return result + "string"  # Potential TypeError

# Nested import errors
try:
    from fake_module import fake_function
    fake_function()
except ImportError:
    pass

# Function call before definition (forward reference)
forward_result = forward_function()

def forward_function():
    return "I'm defined after being called"

# Edge cases
if __name__ == "__main__":
    print("Running comprehensive test...")
    
    # Test all error types
    test_module_not_found()
    test_syntax_errors()
    test_name_errors()
    test_type_errors()
    test_index_errors()
    
print("Test completed!")
