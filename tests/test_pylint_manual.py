# test_pylint_manual.py

from api.services.analyzers import PylintAnalyzer

analyzer = PylintAnalyzer()

# Test 1: Simple code
print("=" * 50)
print("Test 1: Simple code")
print("=" * 50)

code1 = """
def hello():
    x=1
    if x==1:
        print("hello")
"""

result1 = analyzer.analyze(code1)
print(f"Score: {result1['score']}")
print(f"Grade: {result1['grade']}")
print(f"Total Issues: {result1['total_issues']}")
print("\nIssues:")
for issue in result1['issues']:
    print(f"  Line {issue['line']}: [{issue['severity']}] {issue['message']}")

# Test 2: Better code
print("\n" + "=" * 50)
print("Test 2: Better formatted code")
print("=" * 50)

code2 = """
def hello():
    x = 1
    if x == 1:
        print("hello")
"""

result2 = analyzer.analyze(code2)
print(f"Score: {result2['score']}")
print(f"Grade: {result2['grade']}")
print(f"Total Issues: {result2['total_issues']}")

# Test 3: Perfect code
print("\n" + "=" * 50)
print("Test 3: Perfect code with docstrings")
print("=" * 50)

code3 = '''"""Module docstring."""


def hello_world():
    """Say hello to the world."""
    message = "Hello, world!"
    print(message)
'''

result3 = analyzer.analyze(code3)
print(f"Score: {result3['score']}")
print(f"Grade: {result3['grade']}")
print(f"Total Issues: {result3['total_issues']}")
