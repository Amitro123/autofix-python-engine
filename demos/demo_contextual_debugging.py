"""
Full Integration Test: Gemini + Contextual Debugging
"""

# Load environment first
from test_config import get_api_key
import os

# Set API key from environment
os.environ['GEMINI_API_KEY'] = get_api_key()

from api.services.memory_service import MemoryService
from api.services.debugger_service import DebuggerService
from api.services.tools_service import ToolsService
from api.services.gemini_service import GeminiService

print("="*80)
print("🔬 Full Contextual Debugging Test")
print("="*80)

# Initialize with all services
memory = MemoryService()
debugger = DebuggerService()
tools = ToolsService(
    memory_service=memory,
    debugger_service=debugger
)
gemini = GeminiService(tools)

# Test 1: IndexError
print("\n📝 Test 1: IndexError with Variable Tracking")
print("="*80)

broken_code1 = """
numbers = [1, 2, 3, 4, 5]
index = 10
result = numbers[index]
print(result)
"""

print("Broken Code:")
print(broken_code1)

print("\n🤖 Asking Gemini to fix...")
result1 = gemini.process_user_code(broken_code1, max_iterations=3)

print("\n" + "="*80)
if result1['success']:
    print("✅ SUCCESS!")
    print("="*80)
    print(f"\n🔧 Fixed Code:\n{result1['fixed_code']}")
    print(f"\n💡 Explanation:\n{result1['explanation'][:600]}")
else:
    print("❌ Failed")
    print(result1['explanation'])

print(f"\n📊 Stats:")
print(f"  Iterations: {result1['iterations']}")
print(f"  Tools: {[t['tool'] for t in result1['tools_used']]}")

# Test 2: TypeError
print("\n\n📝 Test 2: TypeError with Type Analysis")
print("="*80)

broken_code2 = """
name = "Alice"
age = 25
message = name + age
print(message)
"""

print("Broken Code:")
print(broken_code2)

print("\n🤖 Asking Gemini to fix...")
result2 = gemini.process_user_code(broken_code2, max_iterations=3)

print("\n" + "="*80)
if result2['success']:
    print("✅ SUCCESS!")
    print("="*80)
    print(f"\n🔧 Fixed Code:\n{result2['fixed_code']}")
    print(f"\n💡 Explanation:\n{result2['explanation'][:600]}")
else:
    print("❌ Failed")

print(f"\n📊 Stats:")
print(f"  Iterations: {result2['iterations']}")
print(f"  Tools: {[t['tool'] for t in result2['tools_used']]}")

print("\n" + "="*80)
print("🎉 Contextual Debugging Test Complete!")
print("="*80)
