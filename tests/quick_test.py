# quick_test.py
from api.services.analyzers import PylintAnalyzer

analyzer = PylintAnalyzer()
result = analyzer.analyze("x=1\nif x==1:\n    print(x)")
print(f"Score: {result['score']}, Grade: {result['grade']}, Issues: {result['total_issues']}")
