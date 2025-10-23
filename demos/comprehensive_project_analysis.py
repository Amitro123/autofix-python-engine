#!/usr/bin/env python3
"""
Comprehensive Project Analysis - AutoFix Python Engine
Analyzes test coverage, identifies bugs, and reports open issues.
"""

import ast
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple
import re

class ProjectAnalyzer:
    """Comprehensive analyzer for the AutoFix Python Engine project"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.issues = []
        self.test_coverage = {}
        self.error_handlers = {
            'ModuleNotFoundError': [],
            'TypeError': [],
            'IndexError': [],
            'SyntaxError': [],
            'NameError': [],
            'AttributeError': [],
            'IndentationError': []
        }
        
    def analyze_syntax_validity(self) -> Dict[str, List[str]]:
        """Check all Python files for syntax errors"""
        print("🔍 Analyzing syntax validity...")
        syntax_issues = []
        valid_files = []
        
        for py_file in self.project_root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ['__pycache__', '.git']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.strip():  # Skip empty files
                        ast.parse(content, filename=str(py_file))
                        valid_files.append(str(py_file.relative_to(self.project_root)))
            except SyntaxError as e:
                syntax_issues.append(f"{py_file.relative_to(self.project_root)}: {e}")
            except Exception as e:
                syntax_issues.append(f"{py_file.relative_to(self.project_root)}: {type(e).__name__}: {e}")
        
        return {
            'valid_files': valid_files,
            'syntax_issues': syntax_issues
        }
    
    def analyze_test_coverage(self) -> Dict[str, any]:
        """Analyze test coverage for error handlers"""
        print("🔍 Analyzing test coverage...")
        
        test_files = list(self.project_root.glob("tests/test_*.py"))
        test_scripts = list(self.project_root.glob("test_scripts/*.py"))
        
        coverage_report = {
            'total_test_files': len(test_files),
            'test_script_files': len(test_scripts),
            'error_handler_coverage': {},
            'missing_coverage': []
        }
        
        # Check coverage for each error type
        for error_type in self.error_handlers.keys():
            covered = False
            test_files_for_error = []
            
            # Search in test files
            for test_file in test_files + test_scripts:
                try:
                    with open(test_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if error_type.lower() in content.lower() or error_type in content:
                            covered = True
                            test_files_for_error.append(str(test_file.relative_to(self.project_root)))
                except Exception:
                    continue
            
            coverage_report['error_handler_coverage'][error_type] = {
                'covered': covered,
                'test_files': test_files_for_error
            }
            
            if not covered:
                coverage_report['missing_coverage'].append(error_type)
        
        return coverage_report
    
    def analyze_todo_items(self) -> List[str]:
        """Find all TODO, FIXME, BUG, HACK items"""
        print("🔍 Analyzing TODO items and code issues...")
        
        todo_patterns = [r'TODO', r'FIXME', r'BUG', r'HACK', r'XXX']
        todo_items = []
        
        for py_file in self.project_root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ['__pycache__', '.git']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines, 1):
                        for pattern in todo_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                todo_items.append(f"{py_file.relative_to(self.project_root)}:{i}: {line.strip()}")
            except Exception:
                continue
        
        return todo_items
    
    def analyze_import_issues(self) -> Dict[str, List[str]]:
        """Check for potential import issues"""
        print("🔍 Analyzing import dependencies...")
        
        import_issues = []
        circular_imports = []
        missing_imports = []
        
        for py_file in self.project_root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ['__pycache__', '.git']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for relative imports that might be problematic
                if re.search(r'from\s+\.\s+import', content):
                    import_issues.append(f"{py_file.relative_to(self.project_root)}: Uses relative imports")
                
                # Check for imports that might not exist
                import_matches = re.findall(r'import\s+(\w+)', content)
                from_matches = re.findall(r'from\s+(\w+)', content)
                
                all_imports = set(import_matches + from_matches)
                for imp in all_imports:
                    if imp not in ['sys', 'os', 're', 'json', 'time', 'logging', 'subprocess', 'pathlib']:
                        # Check if it's a local module
                        potential_file = self.project_root / f"{imp}.py"
                        if not potential_file.exists() and imp not in ['requests', 'cv2', 'fabric', 'colorama']:
                            missing_imports.append(f"{py_file.relative_to(self.project_root)}: {imp}")
                            
            except Exception:
                continue
        
        return {
            'import_issues': import_issues,
            'circular_imports': circular_imports,
            'missing_imports': missing_imports
        }
    
    def analyze_error_handling(self) -> Dict[str, any]:
        """Analyze error handling patterns"""
        print("🔍 Analyzing error handling patterns...")
        
        error_handling_report = {
            'files_with_try_catch': [],
            'files_without_error_handling': [],
            'exception_types_caught': set(),
            'bare_except_usage': []
        }
        
        for py_file in self.project_root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ['__pycache__', '.git']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if 'try:' in content:
                    error_handling_report['files_with_try_catch'].append(
                        str(py_file.relative_to(self.project_root))
                    )
                    
                    # Check for bare except
                    if re.search(r'except\s*:', content):
                        error_handling_report['bare_except_usage'].append(
                            str(py_file.relative_to(self.project_root))
                        )
                    
                    # Find specific exception types
                    except_matches = re.findall(r'except\s+(\w+Error|\w+Exception)', content)
                    error_handling_report['exception_types_caught'].update(except_matches)
                else:
                    # Check if file has functions that might need error handling
                    if 'def ' in content and len(content.split('\n')) > 10:
                        error_handling_report['files_without_error_handling'].append(
                            str(py_file.relative_to(self.project_root))
                        )
                        
            except Exception:
                continue
        
        error_handling_report['exception_types_caught'] = list(error_handling_report['exception_types_caught'])
        return error_handling_report
    
    def check_unified_engine_integration(self) -> Dict[str, any]:
        """Check integration between unified engine components"""
        print("🔍 Checking unified engine integration...")
        
        integration_report = {
            'autofix_cli_interactive_exists': False,
            'error_parser_has_parse_error': False,
            'all_handlers_present': False,
            'cli_compatibility': False,
            'missing_methods': []
        }
        
        # Check main unified engine file
        main_engine = self.project_root / "autofix_cli_interactive.py"
        if main_engine.exists():
            integration_report['autofix_cli_interactive_exists'] = True
            
            with open(main_engine, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for all required handlers
            required_handlers = [
                'ModuleNotFoundHandler',
                'TypeErrorHandler', 
                'IndexErrorHandler',
                'SyntaxErrorHandler',
                'IndentationErrorHandler'
            ]
            
            handlers_found = sum(1 for handler in required_handlers if handler in content)
            integration_report['all_handlers_present'] = handlers_found == len(required_handlers)
        
        # Check ErrorParser
        error_parser = self.project_root / "error_parser.py"
        if error_parser.exists():
            with open(error_parser, 'r', encoding='utf-8') as f:
                content = f.read()
                
            integration_report['error_parser_has_parse_error'] = 'def parse_error(' in content
        
        # Check CLI compatibility
        cli_file = self.project_root / "cli.py"
        if cli_file.exists():
            with open(cli_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            integration_report['cli_compatibility'] = 'def print_summary(' in content
        
        return integration_report
    
    def generate_report(self) -> str:
        """Generate comprehensive analysis report"""
        print("📊 Generating comprehensive analysis report...")
        
        syntax_analysis = self.analyze_syntax_validity()
        test_coverage = self.analyze_test_coverage()
        todo_items = self.analyze_todo_items()
        import_analysis = self.analyze_import_issues()
        error_handling = self.analyze_error_handling()
        integration = self.check_unified_engine_integration()
        
        report = []
        report.append("=" * 80)
        report.append("🔍 COMPREHENSIVE PROJECT ANALYSIS - AUTOFIX PYTHON ENGINE")
        report.append("=" * 80)
        
        # Syntax Analysis
        report.append("\n📋 SYNTAX VALIDITY ANALYSIS")
        report.append("-" * 40)
        report.append(f"✅ Valid Python files: {len(syntax_analysis['valid_files'])}")
        if syntax_analysis['syntax_issues']:
            report.append(f"❌ Files with syntax issues: {len(syntax_analysis['syntax_issues'])}")
            for issue in syntax_analysis['syntax_issues'][:5]:
                report.append(f"   - {issue}")
        else:
            report.append("✅ No syntax issues found")
        
        # Test Coverage Analysis
        report.append("\n📋 TEST COVERAGE ANALYSIS")
        report.append("-" * 40)
        report.append(f"📁 Total test files: {test_coverage['total_test_files']}")
        report.append(f"📁 Test script files: {test_coverage['test_script_files']}")
        
        report.append("\n🎯 Error Handler Coverage:")
        for error_type, coverage in test_coverage['error_handler_coverage'].items():
            status = "✅" if coverage['covered'] else "❌"
            report.append(f"   {status} {error_type}: {len(coverage['test_files'])} test files")
        
        if test_coverage['missing_coverage']:
            report.append(f"\n⚠️  Missing test coverage for: {', '.join(test_coverage['missing_coverage'])}")
        
        # TODO Items Analysis
        report.append("\n📋 TODO ITEMS & CODE ISSUES")
        report.append("-" * 40)
        if todo_items:
            report.append(f"📝 Found {len(todo_items)} TODO/FIXME items:")
            for item in todo_items[:10]:  # Show first 10
                report.append(f"   - {item}")
            if len(todo_items) > 10:
                report.append(f"   ... and {len(todo_items) - 10} more")
        else:
            report.append("✅ No TODO/FIXME items found")
        
        # Import Analysis
        report.append("\n📋 IMPORT DEPENDENCY ANALYSIS")
        report.append("-" * 40)
        if import_analysis['import_issues']:
            report.append(f"⚠️  Import issues found: {len(import_analysis['import_issues'])}")
            for issue in import_analysis['import_issues'][:5]:
                report.append(f"   - {issue}")
        
        if import_analysis['missing_imports']:
            report.append(f"❌ Potential missing imports: {len(import_analysis['missing_imports'])}")
            for missing in import_analysis['missing_imports'][:5]:
                report.append(f"   - {missing}")
        
        if not import_analysis['import_issues'] and not import_analysis['missing_imports']:
            report.append("✅ No significant import issues found")
        
        # Error Handling Analysis
        report.append("\n📋 ERROR HANDLING ANALYSIS")
        report.append("-" * 40)
        report.append(f"✅ Files with try/catch: {len(error_handling['files_with_try_catch'])}")
        report.append(f"⚠️  Files without error handling: {len(error_handling['files_without_error_handling'])}")
        report.append(f"📊 Exception types handled: {len(error_handling['exception_types_caught'])}")
        
        if error_handling['bare_except_usage']:
            report.append(f"⚠️  Files using bare except: {len(error_handling['bare_except_usage'])}")
        
        # Integration Analysis
        report.append("\n📋 UNIFIED ENGINE INTEGRATION")
        report.append("-" * 40)
        
        status_items = [
            ("AutoFix CLI Interactive exists", integration['autofix_cli_interactive_exists']),
            ("ErrorParser has parse_error method", integration['error_parser_has_parse_error']),
            ("All error handlers present", integration['all_handlers_present']),
            ("CLI compatibility maintained", integration['cli_compatibility'])
        ]
        
        for item, status in status_items:
            icon = "✅" if status else "❌"
            report.append(f"   {icon} {item}")
        
        # Summary
        report.append("\n📋 SUMMARY & RECOMMENDATIONS")
        report.append("-" * 40)
        
        critical_issues = 0
        if syntax_analysis['syntax_issues']:
            critical_issues += len(syntax_analysis['syntax_issues'])
        if test_coverage['missing_coverage']:
            critical_issues += len(test_coverage['missing_coverage'])
        if not integration['error_parser_has_parse_error']:
            critical_issues += 1
        if not integration['all_handlers_present']:
            critical_issues += 1
        
        if critical_issues == 0:
            report.append("🎉 EXCELLENT: No critical issues found!")
            report.append("✅ The unified AutoFix engine appears to be in good condition")
        else:
            report.append(f"⚠️  Found {critical_issues} critical issues that need attention")
        
        report.append(f"\n📊 Project Health Score: {max(0, 100 - critical_issues * 10)}/100")
        
        report.append("\n" + "=" * 80)
        
        return "\n".join(report)

def main():
    """Run comprehensive project analysis"""
    analyzer = ProjectAnalyzer()
    report = analyzer.generate_report()
    print(report)
    
    # Save report to file
    with open("project_analysis_report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n📄 Full report saved to: project_analysis_report.txt")

if __name__ == "__main__":
    main()
