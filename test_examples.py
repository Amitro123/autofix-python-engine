# Test examples for AutoFix Python Engine

# Example 1: Missing package
import requests
response = requests.get("https://api.github.com")
print(response.json())

# Example 2: Missing local module  
from utils import helper_function
result = helper_function("test")
print(result)

# Example 3: Undefined function
data = process_data([1, 2, 3])
print(data)

# Example 4: Basic syntax error (missing colon)
if True
    print("This has a syntax error")
