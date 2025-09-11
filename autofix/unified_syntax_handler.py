"""
Unified SyntaxError Handler - Centralized syntax error fixing logic
"""
import re
from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class SyntaxErrorType(Enum):
    """Enumeration of different syntax error types"""
    MISSING_COLON = "missing_colon"
    PARENTHESES_MISMATCH = "parentheses_mismatch"
    UNEXPECTED_EOF = "unexpected_eof"
    INVALID_CHARACTER = "invalid_character"
    INDENTATION_SYNTAX = "indentation_syntax"
    PRINT_STATEMENT = "print_statement"
    BROKEN_KEYWORDS = "broken_keywords"
    VERSION_COMPATIBILITY = "version_compatibility"
    GENERAL_SYNTAX = "general_syntax"


@dataclass
class SyntaxFix:
    """Represents a specific syntax fix to apply"""
    fix_type: SyntaxErrorType
    pattern: Optional[str] = None
    replacement: Optional[str] = None
    line_specific: bool = False
    description: str = ""


class UnifiedSyntaxErrorHandler:
    """
    Unified handler for all syntax error types.
    Combines logic from both autofix_cli and python_fixer.
    """
    
    def __init__(self):
        self.keyword_fixes = {
            r'\bi f\b': 'if', r'\bd ef\b': 'def', r'\bc lass\b': 'class',
            r'\be lse\b': 'else', r'\be lif\b': 'elif', r'\bf or\b': 'for',
            r'\bw hile\b': 'while', r'\bt ry\b': 'try', r'\be xcept\b': 'except',
            r'\bf rom\b': 'from', r'\bi mport\b': 'import', r'\br eturn\b': 'return'
        }
        
        self.fixes_registry = self._build_fixes_registry()
    
    def _build_fixes_registry(self) -> Dict[SyntaxErrorType, List[SyntaxFix]]:
        """Build registry of all available syntax fixes"""
        return {
            SyntaxErrorType.MISSING_COLON: [
                SyntaxFix(
                    SyntaxErrorType.MISSING_COLON,
                    r'(def\s+\w+\([^)]*\))\s*(?=[^:])',
                    r'\1: ',
                    description="Add missing colon after function definition"
                ),
                SyntaxFix(
                    SyntaxErrorType.MISSING_COLON,
                    r'\b(if|elif|else|for|while|class|try|except|finally|with)\s+[^:\n]*(?<![:\n])\s*$',
                    r'\g<0>:',
                    description="Add missing colon after control structure"
                )
            ],
            SyntaxErrorType.PRINT_STATEMENT: [
                SyntaxFix(
                    SyntaxErrorType.PRINT_STATEMENT,
                    description="Convert Python 2 print statements to Python 3 function calls"
                )
            ],
            SyntaxErrorType.BROKEN_KEYWORDS: [
                SyntaxFix(
                    SyntaxErrorType.BROKEN_KEYWORDS,
                    description="Fix broken keywords with spaces"
                )
            ]
        }
    
    def can_handle(self, error_output: str) -> bool:
        """Check if this handler can process the error"""
        return "SyntaxError" in error_output
    
    def analyze_error(self, error_output: str, file_path: str = None) -> Tuple[SyntaxErrorType, str, Dict]:
        """
        Unified error analysis combining both approaches
        """
        error_type, suggestion = self._classify_syntax_error(error_output)
        
        # Extract additional details
        details = {
            "error_output": error_output,
            "line_number": self._extract_line_number(error_output),
            "file_path": file_path
        }
        
        # Check for version compatibility issues
        version_issue = self._check_version_compatibility(error_output)
        if version_issue:
            details["version_issue"] = version_issue
            error_type = SyntaxErrorType.VERSION_COMPATIBILITY
        
        return error_type, suggestion, details
    
    def _classify_syntax_error(self, error_output: str) -> Tuple[SyntaxErrorType, str]:
        """Classify the specific type of syntax error"""
        error_output_lower = error_output.lower()
        
        if "invalid syntax" in error_output_lower:
            if "(" in error_output or ")" in error_output:
                return SyntaxErrorType.PARENTHESES_MISMATCH, "Check for missing or extra parentheses"
            elif ":" in error_output or "expected ':'" in error_output_lower:
                return SyntaxErrorType.MISSING_COLON, "Add missing colon after control structures"
            elif "print" in error_output_lower:
                return SyntaxErrorType.PRINT_STATEMENT, "Convert print statement to function call"
            else:
                return SyntaxErrorType.GENERAL_SYNTAX, "Fix syntax error - check keywords and punctuation"
        
        elif "unexpected eof" in error_output_lower:
            return SyntaxErrorType.UNEXPECTED_EOF, "Missing closing parentheses, brackets, or quotes"
        
        elif "invalid character" in error_output_lower:
            return SyntaxErrorType.INVALID_CHARACTER, "Remove invalid characters or fix encoding issues"
        
        elif "indentation" in error_output_lower:
            return SyntaxErrorType.INDENTATION_SYNTAX, "Fix indentation - use consistent spaces or tabs"
        
        else:
            return SyntaxErrorType.GENERAL_SYNTAX, "Fix syntax error - check Python syntax rules"
    
    def _extract_line_number(self, error_output: str) -> Optional[int]:
        """Extract line number from error output"""
        line_match = re.search(r'line (\d+)', error_output)
        return int(line_match.group(1)) if line_match else None
    
    def _check_version_compatibility(self, error_output: str) -> Optional[Dict]:
        """Check for Python version compatibility issues"""
        # Add logic to detect version-specific syntax issues
        if "print" in error_output.lower() and "invalid syntax" in error_output.lower():
            return {
                "feature": "print statement",
                "required_version": "2.x",
                "current_version": "3.x",
                "suggestion": "Use print() function instead of print statement"
            }
        return None
    
    def fix_error(self, file_path: str, error_type: SyntaxErrorType, details: Dict) -> bool:
        """
        Apply the appropriate fix based on error type
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Apply specific fixes based on error type
            if error_type == SyntaxErrorType.MISSING_COLON:
                content = self._fix_missing_colons(content, details)
            
            elif error_type == SyntaxErrorType.PARENTHESES_MISMATCH:
                content = self._fix_parentheses_mismatch(content)
            
            elif error_type == SyntaxErrorType.UNEXPECTED_EOF:
                content = self._fix_unexpected_eof(content)
            
            elif error_type == SyntaxErrorType.PRINT_STATEMENT:
                content = self._fix_print_statements(content)
            
            elif error_type == SyntaxErrorType.BROKEN_KEYWORDS:
                content = self._fix_broken_keywords(content)
            
            elif error_type == SyntaxErrorType.INDENTATION_SYNTAX:
                content = self._fix_basic_indentation(content)
            
            else:
                # Apply general fixes
                content = self._apply_general_fixes(content, details)
            
            # Write back if changes were made
            if content != original_content:
                # Create backup first
                self._create_backup(file_path)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                return True
            
            return False
            
        except Exception as e:
            print(f"Failed to fix syntax error: {e}")
            return False
    
    def _fix_missing_colons(self, content: str, details: Dict) -> str:
        """Fix missing colons after control structures"""
        # Fix function definitions first
        content = re.sub(r'(def\s+\w+\([^)]*\))\s*(?=[^:])', r'\1: ', content)
        
        # Fix control structures
        content = re.sub(
            r'\b(if|elif|else|for|while|class|try|except|finally|with)\s+[^:\n]*(?<![:\n])\s*$',
            r'\g<0>:',
            content,
            flags=re.MULTILINE
        )
        
        return content
    
    def _fix_parentheses_mismatch(self, content: str) -> str:
        """Basic parentheses balancing"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            open_count = line.count('(')
            close_count = line.count(')')
            
            if open_count > close_count:
                lines[i] = line + ')' * (open_count - close_count)
            elif close_count > open_count and i > 0:
                lines[i-1] = lines[i-1] + '(' * (close_count - open_count)
        
        return '\n'.join(lines)
    
    def _fix_unexpected_eof(self, content: str) -> str:
        """Add missing closing characters"""
        # Fix unmatched quotes
        if content.count('"') % 2 == 1:
            content += '"'
        if content.count("'") % 2 == 1:
            content += "'"
        
        # Fix unmatched brackets
        bracket_pairs = [('(', ')'), ('[', ']'), ('{', '}')]
        
        for open_char, close_char in bracket_pairs:
            open_count = content.count(open_char)
            close_count = content.count(close_char)
            if open_count > close_count:
                content += close_char * (open_count - close_count)
        
        return content
    
    def _fix_print_statements(self, content: str) -> str:
        """Convert Python 2 print statements to Python 3"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if 'print ' in line and not line.strip().startswith('#'):
                if 'print(' not in line:
                    # Simple conversion: print x -> print(x)
                    lines[i] = re.sub(r'print\s+([^#\n]+)', r'print(\1)', line)
        
        return '\n'.join(lines)
    
    def _fix_broken_keywords(self, content: str) -> str:
        """Fix keywords that have been broken with spaces"""
        for pattern, replacement in self.keyword_fixes.items():
            content = re.sub(pattern, replacement, content)
        
        return content
    
    def _fix_basic_indentation(self, content: str) -> str:
        """Apply basic indentation fixes"""
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                # Check if this should be indented
                if any(keyword in line for keyword in ['return ', 'print(', 'pass', '=']):
                    # Look at previous line
                    if formatted_lines and formatted_lines[-1].strip().endswith(':'):
                        line = '    ' + line
            
            formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def _apply_general_fixes(self, content: str, details: Dict) -> str:
        """Apply general syntax fixes"""
        # Apply all basic fixes
        content = self._fix_broken_keywords(content)
        content = self._fix_missing_colons(content, details)
        content = self._fix_unexpected_eof(content)
        
        return content
    
    def _create_backup(self, file_path: str) -> None:
        """Create backup of original file"""
        import shutil
        backup_path = f"{file_path}.backup"
        shutil.copy2(file_path, backup_path)
    
    def get_error_name(self) -> str:
        return "SyntaxError"
    
    def generate_fix_suggestions(self, error_type: SyntaxErrorType) -> List[str]:
        """Generate human-readable fix suggestions"""
        suggestions = []
        
        if error_type in self.fixes_registry:
            for fix in self.fixes_registry[error_type]:
                suggestions.append(fix.description)
        
        if not suggestions:
            suggestions.append("Apply automatic syntax fixes")
        
        return suggestions


# Factory function to create the handler
def create_syntax_error_handler() -> UnifiedSyntaxErrorHandler:
    """Factory function to create a unified syntax error handler"""
    return UnifiedSyntaxErrorHandler()


# Usage example:
"""
handler = create_syntax_error_handler()

if handler.can_handle(error_output):
    error_type, suggestion, details = handler.analyze_error(error_output, file_path)
    success = handler.fix_error(file_path, error_type, details)
    
    if success:
        print(f"Fixed {error_type.value}: {suggestion}")
    else:
        suggestions = handler.generate_fix_suggestions(error_type)
        print(f"Manual fixes needed: {suggestions}")
"""