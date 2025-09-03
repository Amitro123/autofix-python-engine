#!/usr/bin/env python3
"""
AttributeError test cases for AutoFix
"""

# Test case 1: NoneType attribute access
def test_none_type():
    obj = None
    return obj.some_attribute  # This will cause AttributeError

# Test case 2: String attribute error (common typo)
def test_string_error():
    text = "hello world"
    text.append("!")  # Strings don't have append method
    return text

# Test case 3: List attribute error (common typo)
def test_list_error():
    my_list = [1, 2, 3]
    return my_list.length  # Lists don't have length attribute

# Test case 4: Dictionary attribute error
def test_dict_error():
    my_dict = {"key": "value"}
    return my_dict.size  # Dicts don't have size attribute

if __name__ == "__main__":
    # This will trigger AttributeError
    test_none_type()
