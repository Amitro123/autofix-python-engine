"""
Pylint integration for Python code style checking.

Analyzes code for:
- PEP8 compliance
- Best practices
- Code smells
- Potential bugs
"""

from typing import Dict, List, Optional
import tempfile
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass


@dataclass
class PylintIssue:
    """Represents a single Pylint issue."""
    line: int
    column: int
    severity: str  # error, warning, convention, refactor
    message: str
    rule_id: str
    symbol: str
    
    def to_dict(self) -> Dict:
        return {
            'line': self.line,
            'column': self.column,
            'severity': self.severity,
            'message': self.message,
            'rule_id': self.rule_id,
            'symbol': self.symbol
        }


class PylintAnalyzer:
    """
    Wrapper around Pylint for code analysis.
    
    Usage:
        analyzer = PylintAnalyzer()
        result = analyzer.analyze("def foo():\n  x=1")
        print(result['score'])  # 8.5
        print(result['issues'])  # [...]
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Pylint analyzer.
        
        Args:
            config: Optional Pylint configuration
        """
        self.config = config or self._default_config()
    
    def analyze(self, code: str) -> Dict:
        """
        Analyze Python code with Pylint.
        
        Args:
            code: Python code to analyze
            
        Returns:
            {
                'score': 8.5,  # 0-10 scale
                'issues': [...],  # List of issues
                'grade': 'B+',  # Letter grade
                'stats': {...}  # Statistics
            }
        """
        # Write code to temporary file
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.py', 
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            # Run Pylint
            result = self._run_pylint(temp_path)
            
            # Parse and return results
            return self._parse_results(result)
        
        finally:
            # Cleanup temporary file
            temp_path.unlink(missing_ok=True)
    
    def _run_pylint(self, file_path: Path) -> Dict:
        """
        Run Pylint on a file.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Pylint output as dict
        """
        # Build Pylint command
        cmd = [
            'pylint',
            str(file_path),
            '--output-format=json',
            '--score=yes',
            # Disable some noisy checks for user code
            '--disable=missing-module-docstring',
            '--disable=invalid-name',
            '--max-line-length=120'
        ]
        
        # Run Pylint
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Parse JSON output
            if result.stdout.strip():
                issues = json.loads(result.stdout)
            else:
                issues = []
            
            # Extract score from stderr (Pylint prints score there)
            score = self._extract_score(result.stderr)
            
            return {
                'issues': issues,
                'score': score,
                'returncode': result.returncode
            }
        
        except subprocess.TimeoutExpired:
            return {
                'issues': [],
                'score': 0.0,
                'error': 'Pylint timeout'
            }
        
        except json.JSONDecodeError as e:
            return {
                'issues': [],
                'score': 0.0,
                'error': f'Failed to parse Pylint output: {e}'
            }
    
    def _extract_score(self, stderr: str) -> float:
        """
        Extract score from Pylint stderr output.
        
        Pylint prints something like:
        "Your code has been rated at 8.50/10"
        """
        import re
        
        match = re.search(r'rated at ([\d.]+)/10', stderr)
        if match:
            return float(match.group(1))
        return 10.0  # Default to perfect if no issues
    
    def _parse_results(self, result: Dict) -> Dict:
        """
        Parse Pylint results into our format.
        
        Args:
            result: Raw Pylint output
            
        Returns:
            Structured analysis result
        """
        issues = []
        
        # Parse each issue
        for item in result.get('issues', []):
            issue = PylintIssue(
                line=item.get('line', 0),
                column=item.get('column', 0),
                severity=item.get('type', 'warning').lower(),
                message=item.get('message', ''),
                rule_id=item.get('message-id', ''),
                symbol=item.get('symbol', '')
            )
            issues.append(issue)
        
        # Calculate statistics
        stats = self._calculate_stats(issues)
        
        # Get score
        score = result.get('score', 10.0)
        
        # Calculate grade
        grade = self._score_to_grade(score)
        
        return {
            'score': round(score, 2),
            'grade': grade,
            'issues': [issue.to_dict() for issue in issues],
            'stats': stats,
            'total_issues': len(issues)
        }
    
    def _calculate_stats(self, issues: List[PylintIssue]) -> Dict:
        """Calculate statistics from issues."""
        stats = {
            'error': 0,
            'warning': 0,
            'convention': 0,
            'refactor': 0
        }
        
        for issue in issues:
            severity = issue.severity.lower()
            if severity in stats:
                stats[severity] += 1
        
        return stats
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 9.5:
            return 'A+'
        elif score >= 9.0:
            return 'A'
        elif score >= 8.5:
            return 'A-'
        elif score >= 8.0:
            return 'B+'
        elif score >= 7.5:
            return 'B'
        elif score >= 7.0:
            return 'B-'
        elif score >= 6.5:
            return 'C+'
        elif score >= 6.0:
            return 'C'
        elif score >= 5.5:
            return 'C-'
        elif score >= 5.0:
            return 'D'
        else:
            return 'F'
    
    def _default_config(self) -> Dict:
        """Default Pylint configuration."""
        return {
            'max_line_length': 120,
            'disable': [
                'missing-module-docstring',
                'invalid-name',
            ]
        }
