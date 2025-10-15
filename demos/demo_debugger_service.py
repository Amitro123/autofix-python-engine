"""
Demo: Test Enhanced Debugger
"""

# Load environment first
from test_config import get_api_key
import os

# Set API key from environment
os.environ['GEMINI_API_KEY'] = get_api_key()

from api.services.debugger_service import DebuggerService
import json

debugger = DebuggerService()

# Rest of the test code stays the same...
print("="*80)
print("Test 1: IndexError with Variable Tracking")
print("="*80)

code1 = """
data_points = [1, 2, 3]
requested_index = 10
result = data_points[requested_index]
print(result)
"""

result1 = debugger.execute_with_trace(code1)

print(f"\n✅ Success: {result1['success']}")
print(f"❌ Error Type: {result1['error_type']}")
print(f"📍 Error Line: {result1['error_line']}")
print(f"\n📊 Variables at Error:")
print(json.dumps(result1['variables_at_error'], indent=2))

# Test 2: TypeError
print("\n" + "=" * 80)
print("Test 2: TypeError")
print("=" * 80)

code2 = """
x = "5"
y = 3
result = x + y
"""

result2 = debugger.execute_with_trace(code2)

print(f"\n✅ Success: {result2['success']}")
print(f"❌ Error: {result2['error_type']}: {result2['error_message']}")
print(f"\n📊 Variables at Error:")
print(json.dumps(result2['variables_at_error'], indent=2))
