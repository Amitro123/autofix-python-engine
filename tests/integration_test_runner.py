#!/usr/bin/env python3
"""
Integration Test Runner for AutoFix CLI
Runs the CLI against all test_*.py files and validates outcomes
"""

import os
import subprocess
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class TestResult:
    """Result of running AutoFix on a test file"""
    filename: str
    success: bool
    exit_code: int
    output: str
    error: str
    expected_outcome: str
    actual_outcome: str

class IntegrationTestRunner:
    """Runs AutoFix CLI against test files and validates results"""
    
    def __init__(self, test_dir: str = "tests"):
        self.test_dir = Path(test_dir)
        self.results: List[TestResult] = []
        
        # Expected outcomes for specific test files
        self.expected_outcomes = {
            "test_clean_demo.py": "SUCCESS",
            "test_name_error.py": "SUCCESS", 
            "test_missing_module.py": "SUCCESS",
            "test_simple_missing.py": "SUCCESS",
            "test_missing_init.py": "SUCCESS",
            "test_missing_nested.py": "SUCCESS",
            "test_symbol_import.py": "SUCCESS",
            "test_custom_function.py": "SUCCESS",
            "test_syntax_fix.py": "SUCCESS",
            "test_missing_package.py": "SUCCESS",
            "test_pip_integration.py": "SUCCESS",
            "test_pip_demo.py": "SUCCESS",
            "test_pip_conflicts.py": "FAILED",  # Expected to fail - complex dependency conflicts
            "test_syntax_error.py": "FAILED",  # Expected to fail - intentional syntax errors
            "test_resolution_impossible.py": "FAILED",  # Expected to fail
            "test_conflict_demo.py": "FAILED",  # Expected to fail - conflicts
        }
    
    def find_test_files(self) -> List[Path]:
        """Find all test_*.py files in the directory"""
        test_files = list(self.test_dir.glob("test_*.py"))
        # Filter out files that are too large or problematic
        excluded = {"test_autofix_demo.py", "test_extension_demo.py", "test_vscode_extension.py"}
        return [f for f in test_files if f.name not in excluded]
    
    def run_autofix_on_file(self, test_file: Path) -> TestResult:
        """Run AutoFix CLI on a single test file"""
        print(f"Testing: {test_file.name}")
        
        try:
            # Run AutoFix CLI with timeout
            cmd = [sys.executable, "../cli.py", str(test_file), "--quiet"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                cwd=str(self.test_dir)
            )
            
            # Determine success based on exit code
            success = result.returncode == 0
            actual_outcome = "SUCCESS" if success else "FAILED"
            expected_outcome = self.expected_outcomes.get(test_file.name, "SUCCESS")
            
            return TestResult(
                filename=test_file.name,
                success=success,
                exit_code=result.returncode,
                output=result.stdout,
                error=result.stderr,
                expected_outcome=expected_outcome,
                actual_outcome=actual_outcome
            )
            
        except subprocess.TimeoutExpired:
            return TestResult(
                filename=test_file.name,
                success=False,
                exit_code=-1,
                output="",
                error="TIMEOUT",
                expected_outcome=self.expected_outcomes.get(test_file.name, "SUCCESS"),
                actual_outcome="TIMEOUT"
            )
        except Exception as e:
            return TestResult(
                filename=test_file.name,
                success=False,
                exit_code=-2,
                output="",
                error=str(e),
                expected_outcome=self.expected_outcomes.get(test_file.name, "SUCCESS"),
                actual_outcome="ERROR"
            )
    
    def run_all_tests(self) -> None:
        """Run AutoFix on all test files"""
        test_files = self.find_test_files()
        print(f"Found {len(test_files)} test files to process")
        print("=" * 60)
        
        for test_file in sorted(test_files):
            result = self.run_autofix_on_file(test_file)
            self.results.append(result)
            
            # Print immediate feedback
            status = "[PASS]" if result.actual_outcome == result.expected_outcome else "[FAIL]"
            print(f"{status} {result.filename}: {result.actual_outcome} (expected: {result.expected_outcome})")
    
    def generate_report(self) -> Dict:
        """Generate a comprehensive test report"""
        total_tests = len(self.results)
        correct_predictions = sum(1 for r in self.results if r.actual_outcome == r.expected_outcome)
        
        # Categorize results
        successes = [r for r in self.results if r.success]
        failures = [r for r in self.results if not r.success]
        unexpected_failures = [r for r in self.results if r.expected_outcome == "SUCCESS" and not r.success]
        unexpected_successes = [r for r in self.results if r.expected_outcome == "FAILED" and r.success]
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "successful_fixes": len(successes),
                "failed_fixes": len(failures),
                "correct_predictions": correct_predictions,
                "accuracy": correct_predictions / total_tests if total_tests > 0 else 0,
            },
            "unexpected_results": {
                "unexpected_failures": [r.filename for r in unexpected_failures],
                "unexpected_successes": [r.filename for r in unexpected_successes],
            },
            "detailed_results": [
                {
                    "filename": r.filename,
                    "success": r.success,
                    "exit_code": r.exit_code,
                    "expected": r.expected_outcome,
                    "actual": r.actual_outcome,
                    "error": r.error if r.error else None
                }
                for r in self.results
            ]
        }
        
        return report
    
    def print_summary(self) -> None:
        """Print a summary of test results"""
        report = self.generate_report()
        summary = report["summary"]
        
        print("\n" + "=" * 60)
        print("AUTOFIX INTEGRATION TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Successful Fixes: {summary['successful_fixes']}")
        print(f"Failed Fixes: {summary['failed_fixes']}")
        print(f"Prediction Accuracy: {summary['accuracy']:.1%}")
        
        # Show unexpected results
        unexpected = report["unexpected_results"]
        if unexpected["unexpected_failures"]:
            print(f"\n[FAIL] Unexpected Failures ({len(unexpected['unexpected_failures'])}):")
            for filename in unexpected["unexpected_failures"]:
                print(f"  - {filename}")
        
        if unexpected["unexpected_successes"]:
            print(f"\n[PASS] Unexpected Successes ({len(unexpected['unexpected_successes'])}):")
            for filename in unexpected["unexpected_successes"]:
                print(f"  - {filename}")
        
        print("\n" + "=" * 60)
    
    def save_report(self, filename: str = "integration_test_report.json") -> None:
        """Save detailed report to JSON file"""
        report = self.generate_report()
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Detailed report saved to: {filename}")

def main():
    """Main entry point"""
    print("AutoFix Integration Test Runner")
    print("Testing CLI against all test_*.py files...")
    print()
    
    runner = IntegrationTestRunner()
    runner.run_all_tests()
    runner.print_summary()
    runner.save_report()

if __name__ == "__main__":
    main()