#!/usr/bin/env python3
"""
Simple TypeError test
"""

# This will cause TypeError: can only concatenate str (not "int") to str
result = "Hello" + str(123)
print(result)
