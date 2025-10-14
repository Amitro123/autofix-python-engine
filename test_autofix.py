"""
Test AutoFix Service
"""

import os

# Set API key
os.environ['GEMINI_API_KEY'] = 'AIzaSyAaA2JfF305khYDWuJkBCMRUL2JHxJc4wI'

from api.services.autofix_service import AutoFixService

# Create service
print("Initializing AutoFix service...")
service = AutoFixService(mode='ai')

# Test 1: IndexError
print("\n" + "="*80)
print("Test 1: IndexError")
print("="*80)

broken_code = """
x = [1, 2, 3]
print(x[10])
"""

print("\n🔧 Fixing code...")
result = service.fix_code(broken_code, max_iterations=3)

print(f"\n{'✅ SUCCESS!' if result['success'] else '❌ FAILED'}")
print(f"Iterations: {result['iterations']}")
print(f"Tools used: {len(result['tools_used'])}")

if result['success']:
    print(f"\n📝 Fixed Code:\n{result['fixed_code']}")
    print(f"\n💡 Explanation:\n{result['explanation'][:300]}...")
else:
    print(f"\n❌ Error: {result['explanation']}")

# Test 2: TypeError
print("\n" + "="*80)
print("Test 2: TypeError")
print("="*80)

broken_code2 = """
result = '5' + 3
print(result)
"""

print("\n🔧 Fixing code...")
result2 = service.fix_code(broken_code2, max_iterations=3)

print(f"\n{'✅ SUCCESS!' if result2['success'] else '❌ FAILED'}")
print(f"Iterations: {result2['iterations']}")

if result2['success']:
    print(f"\n📝 Fixed Code:\n{result2['fixed_code']}")
