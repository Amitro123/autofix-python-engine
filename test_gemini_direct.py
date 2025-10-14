"""
Test Gemini Service Directly
"""

import os

# Set API key
os.environ['GEMINI_API_KEY'] = 'AIzaSyAaA2JfF305khYDWuJkBCMRUL2JHxJc4wI'

from api.services.tools_service import ToolsService
from api.services.gemini_service import GeminiService

# Create services
print("Initializing services...")
tools_service = ToolsService()
gemini_service = GeminiService(tools_service)

# Test code
broken_code = """
x = [1, 2, 3]
print(x[10])
"""

print("\n" + "="*80)
print("Testing Gemini AI Code Fixing")
print("="*80)
print(f"\nBroken code:\n{broken_code}")

print("\n Asking Gemini to fix it...")

# Fix code
result = gemini_service.process_user_code(broken_code, max_iterations=3)

print("\n" + "="*80)
if result['success']:
    print(" SUCCESS!")
    print("="*80)
    print(f"\nIterations: {result['iterations']}")
    print(f"Tools used: {len(result['tools_used'])}")
    
    print(f"\n Fixed Code:\n")
    print(result['fixed_code'])
    
    print(f"\n Explanation:\n")
    print(result['explanation'][:500])
    
else:
    print(" FAILED")
    print("="*80)
    print(result['explanation'])

print("\n" + "="*80)
