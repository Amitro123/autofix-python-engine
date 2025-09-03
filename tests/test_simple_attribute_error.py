#!/usr/bin/env python3
"""
Simple AttributeError test
"""

# This will cause AttributeError: 'str' object has no attribute 'append'
text = "hello"
text += " world"
print(text)
