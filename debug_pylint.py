# debug_pylint.py
from api.services.analyzers import PylintAnalyzer

analyzer = PylintAnalyzer()

code = '''
def foo():
    x=1
    if x==1:
        print(x)
'''

result = analyzer.analyze(code)

print(f"Score: {result['score']}")
print(f"Grade: {result['grade']}")
print(f"Total Issues: {result['total_issues']}")
print(f"\nIssues:")
for issue in result['issues']:
    print(f"  Line {issue['line']}: [{issue['severity']}] {issue['message']} ({issue['rule_id']})")
