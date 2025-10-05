#!/usr/bin/env python3
"""
Smart AutoFix Integration Test Runner
Runs AutoFix against various test cases and validates outcomes
"""

import os
import subprocess
import sys
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class TestCase:
    """A test case with expected behavior"""
    name: str
    code: str
    expected_outcome: str  # "SUCCESS", "FAILED", "PARTIAL"
    description: str


@dataclass
class TestResult:
    """Result of running AutoFix on a test case"""
    name: str
    success: bool
    output: str
    error: str
    expected_outcome: str
    actual_outcome: str
    description: str


class SmartTestRunner:
    """Runs AutoFix against predefined test cases"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.test_cases = self._create_test_cases()
    
    def _create_test_cases(self) -> List[TestCase]:
        """Create comprehensive test cases covering common scenarios"""
        return [
            # ✅ Should succeed - Simple import fixes
            TestCase(
                name="simple_import_typo",
                code="imprt os\nprint('hello')",
                expected_outcome="SUCCESS",
                description="Simple import typo that should be auto-fixed"
            ),
            TestCase(
                name="missing_common_module",
                code="import requests\nresponse = requests.get('https://api.github.com')",
                expected_outcome="SUCCESS", 
                description="Missing common module that should suggest pip install"
            ),
            TestCase(
                name="numpy_alias_fix",
                code="import numpy as npy\narray = npy.array([1,2,3])",
                expected_outcome="SUCCESS",
                description="NumPy import that should be fixed to standard alias"
            ),
            TestCase(
                name="pandas_basic_import",
                code="import pandas\ndf = pandas.DataFrame({'a': [1,2,3]})",
                expected_outcome="SUCCESS",
                description="Pandas import that should suggest standard alias"
            ),
            # Logic Errors (PARTIAL)
            TestCase(
                name="index_out_of_range",
                code="lst = [1,2,3]\nprint(lst[10])",
                expected_outcome="PARTIAL",
                description="IndexError - list index out of range"
            ),

            TestCase(
                name="key_error",
                code="d = {'a': 1}\nprint(d['b'])",
                expected_outcome="PARTIAL", 
                description="KeyError - missing dictionary key"
            ),

            TestCase(
                name="zero_division",
                code="x = 10 / 0",
                expected_outcome="PARTIAL",
                description="ZeroDivisionError"
            ),

            # Import variations (SUCCESS)
            TestCase(
                name="relative_import",
                code="from . import utils",
                expected_outcome="FAILED",  # Can't auto-fix without context
                description="Relative import without package"
            ),

            TestCase(
                name="multiple_imports",
                code="import os, sys, json\nimport requests",
                expected_outcome="SUCCESS",  # requests auto-installed!
                description="Multiple imports with missing package"
            ),

            
            # ✅ Should succeed - Simple syntax fixes  
            TestCase(
                name="missing_colon",
                code="if True\n    print('hello')",
                expected_outcome="SUCCESS",
                description="Missing colon in if statement"
            ),
            TestCase(
                name="simple_indentation",
                code="def test():\nprint('hello')",
                expected_outcome="SUCCESS", 
                description="Simple indentation error"
            ),
            TestCase(
                name="missing_parenthesis",
                code="print 'hello world'",
                expected_outcome="SUCCESS",
                description="Python 2 style print statement"
            ),
            
            # ✅ Should succeed - Type and name errors
            TestCase(
                name="simple_name_error",
                code="x = 5\nprint(y)",
                expected_outcome="PARTIAL",
                description="Simple NameError - should suggest correction"
            ),
            TestCase(
                name="string_concatenation",
                code="result = 'hello' + 5",
                expected_outcome="PARTIAL", 
                description="Type error in string concatenation"
            ),
            
            # ❌ Should fail gracefully - Complex issues
            TestCase(
                name="complex_syntax_error",
                code="def broken_function(\n    invalid syntax here\n    return None",
                expected_outcome="FAILED",
                description="Complex syntax error that cannot be auto-fixed"
            ),
            TestCase(
                name="circular_import",
                code="from module_a import function_that_imports_this_file",
                expected_outcome="FAILED", 
                description="Circular import that cannot be resolved"
            ),
            TestCase(
                name="unknown_library",
                code="import very_obscure_nonexistent_library_12345",
                expected_outcome="FAILED",
                description="Import of non-existent obscure library"
            ),
            
            # 🟡 Partial success - Should provide helpful suggestions
            TestCase(
                name="deprecated_method",
                code="import matplotlib.pyplot as plt\nplt.hold(True)",
                expected_outcome="PARTIAL",
                description="Deprecated matplotlib method usage"
            ),
            TestCase(
                name="general_syntax_error",
                code="x = 10 +",
                expected_outcome="FAILED",
                description="General syntax error that should show user-friendly message"
            ),
        ]
    
    def run_test_case(self, test_case: TestCase) -> TestResult:
        """Run AutoFix on a single test case"""
        print(f"Testing: {test_case.name}")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_case.code)
            temp_file = f.name
        
        try:
            # Run AutoFix
            cmd = [sys.executable, '-m', 'autofix', temp_file, '--auto-fix']
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.getcwd()
            )
            
            # Analyze output
            success = result.returncode == 0
            output = result.stdout.strip()
            error = result.stderr.strip()
            
            # Determine actual outcome
            if "manual review" in output.lower() or "partial" in output.lower():
                actual_outcome = "PARTIAL"
            elif "cannot resolve automatically" in output.lower():
                actual_outcome = "FAILED"
            elif success and not error:
                actual_outcome = "SUCCESS"
            elif output and not error:
                actual_outcome = "PARTIAL"
            else:
                actual_outcome = "FAILED"

            
            return TestResult(
                name=test_case.name,
                success=success,
                output=output,
                error=error,
                expected_outcome=test_case.expected_outcome,
                actual_outcome=actual_outcome,
                description=test_case.description
            )
            
        except subprocess.TimeoutExpired:
            return TestResult(
                name=test_case.name,
                success=False,
                output="",
                error="TIMEOUT",
                expected_outcome=test_case.expected_outcome,
                actual_outcome="TIMEOUT",
                description=test_case.description
            )
        except Exception as e:
            return TestResult(
                name=test_case.name,
                success=False,
                output="",
                error=str(e),
                expected_outcome=test_case.expected_outcome,
                actual_outcome="ERROR",
                description=test_case.description
            )
        finally:
            # Cleanup
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def run_all_tests(self) -> None:
        """Run all test cases"""
        print("🧪 SMART AUTOFIX INTEGRATION TEST")
        print("=" * 60)
        print(f"Running {len(self.test_cases)} comprehensive test cases...")
        print()
        
        for test_case in self.test_cases:
            result = self.run_test_case(test_case)
            self.results.append(result)
            
            # Immediate feedback
            is_correct = result.actual_outcome == result.expected_outcome
            status = "✅ PASS" if is_correct else "❌ FAIL"
            print(f"{status} {result.name}: {result.actual_outcome} (expected: {result.expected_outcome})")
            
            if not is_correct:
                print(f"   📝 {result.description}")
                if result.output:
                    print(f"   💬 Output: {result.output[:100]}...")
    
    def print_summary(self) -> None:
        """Print comprehensive summary"""
        total = len(self.results)
        correct = sum(1 for r in self.results if r.actual_outcome == r.expected_outcome)
        successes = sum(1 for r in self.results if r.success)
        
        # Categorize results
        unexpected_failures = [r for r in self.results if r.expected_outcome == "SUCCESS" and r.actual_outcome != "SUCCESS"]
        unexpected_successes = [r for r in self.results if r.expected_outcome == "FAILED" and r.success]
        
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("=" * 60)
        print(f"📈 Total Test Cases: {total}")
        print(f"✅ Correct Predictions: {correct}/{total} ({correct/total:.1%})")
        print(f"🎯 Successful Auto-fixes: {successes}")
        print(f"⚠️  Issues Found: {len(unexpected_failures)}")
        
        if unexpected_failures:
            print(f"\n❌ UNEXPECTED FAILURES ({len(unexpected_failures)}):")
            for result in unexpected_failures:
                print(f"   • {result.name}: {result.description}")
                if result.error:
                    print(f"     Error: {result.error[:100]}...")
        
        if unexpected_successes:
            print(f"\n🎉 UNEXPECTED SUCCESSES ({len(unexpected_successes)}):")
            for result in unexpected_successes:
                print(f"   • {result.name}: {result.description}")
        
        # Overall assessment
        if correct/total >= 0.8:
            print(f"\n🎉 EXCELLENT! AutoFix is working very well!")
        elif correct/total >= 0.6:
            print(f"\n👍 GOOD! AutoFix is working well with some areas for improvement.")
        else:
            print(f"\n⚠️  NEEDS ATTENTION! Several test cases are not behaving as expected.")
        
        print("=" * 60)
    
    def save_detailed_report(self, filename: str = "smart_test_report.json") -> None:
        """Save detailed JSON report"""
        report = {
            "summary": {
                "total_tests": len(self.results),
                "correct_predictions": sum(1 for r in self.results if r.actual_outcome == r.expected_outcome),
                "successful_fixes": sum(1 for r in self.results if r.success),
                "accuracy": sum(1 for r in self.results if r.actual_outcome == r.expected_outcome) / len(self.results)
            },
            "results": [
                {
                    "name": r.name,
                    "description": r.description,
                    "expected": r.expected_outcome,
                    "actual": r.actual_outcome,
                    "success": r.success,
                    "output": r.output,
                    "error": r.error,
                    "correct_prediction": r.actual_outcome == r.expected_outcome
                }
                for r in self.results
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"📄 Detailed report saved to: {filename}")


def main():
    """Main entry point"""
    # Ensure we're in the right directory
    if not os.path.exists('autofix'):
        print("❌ Error: autofix directory not found. Please run from project root.")
        print("Current directory:", os.getcwd())
        sys.exit(1)
    
    runner = SmartTestRunner()
    runner.run_all_tests()
    runner.print_summary()
    runner.save_detailed_report()


if __name__ == "__main__":
    main()
