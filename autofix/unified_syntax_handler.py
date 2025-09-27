"""
Unified SyntaxError Handler - Complete Final Version
Centralized syntax error fixing logic with improved colon detection
"""
import re
import shutil
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
        # Control structure patterns for fixing missing colons
        self.control_structure_patterns = [
            r'^(\s*)(if\s+.+?)(\s*#.*)?$',           # if condition
            r'^(\s*)(elif\s+.+?)(\s*#.*)?$',         # elif condition  
            r'^(\s*)(else)(\s*#.*)?$',               # else
            r'^(\s*)(for\s+.+?)(\s*#.*)?$',          # for loop
            r'^(\s*)(while\s+.+?)(\s*#.*)?$',        # while loop
            r'^(\s*)(class\s+\w+.*?)(\s*#.*)?$',     # class definition
            r'^(\s*)(def\s+\w+\([^)]*\))(\s*#.*)?$', # function definition
            r'^(\s*)(try)(\s*#.*)?$',                # try
            r'^(\s*)(except.*?)(\s*#.*)?$',          # except
            r'^(\s*)(finally)(\s*#.*)?$',            # finally
            r'^(\s*)(with\s+.+?)(\s*#.*)?$'          # with statement
        ]
        
        # Keyword fixes for broken keywords
        self.keyword_fixes = {
            r'\bi f\b': 'if', r'\bd ef\b': 'def', r'\bc lass\b': 'class',
            r'\be lse\b': 'else', r'\be lif\b': 'elif', r'\bf or\b': 'for',
            r'\bw hile\b': 'while', r'\bt ry\b': 'try', r'\be xcept\b': 'except',
            r'\bf rom\b': 'from', r'\bi mport\b': 'import', r'\br eturn\b': 'return'
        }
        
        # Detection patterns for error classification
        self.detection_patterns = {
            "missing_colon": [r"expected ':'", r"invalid syntax.*:"],
            "unexpected_eof": [r"unexpected EOF", r"EOF while scanning"],
            "invalid_character": [r"invalid character", r"non-ASCII character"],
            "parentheses_mismatch": [r"[()]\s*(invalid syntax|unexpected)", r"unmatched"],
            "print_statement": [
                r"missing parentheses in call to 'print'", 
                r"invalid syntax.*print\s+",
                r"print.*invalid syntax"
            ]
        }
        
        self.fixes_registry = self._build_fixes_registry()
    
    def _build_fixes_registry(self) -> Dict[SyntaxErrorType, List[SyntaxFix]]:
        """Build registry of all available syntax fixes"""
        return {
            SyntaxErrorType.MISSING_COLON: [
                SyntaxFix(
                    SyntaxErrorType.MISSING_COLON,
                    description="Add missing colon after control structures (if, for, while, def, class, etc.)"
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
                    description="Fix broken keywords with spaces (e.g., 'd ef' -> 'def')"
                )
            ],
            SyntaxErrorType.PARENTHESES_MISMATCH: [
                SyntaxFix(
                    SyntaxErrorType.PARENTHESES_MISMATCH,
                    description="Balance mismatched parentheses"
                )
            ],
            SyntaxErrorType.UNEXPECTED_EOF: [
                SyntaxFix(
                    SyntaxErrorType.UNEXPECTED_EOF,
                    description="Add missing closing quotes, brackets, or parentheses"
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
        """Classify the specific type of syntax error using detection patterns"""
        error_output_lower = error_output.lower()
        
        # Check each detection pattern
        for error_key, patterns in self.detection_patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_output_lower):
                    if error_key == "missing_colon":
                        return SyntaxErrorType.MISSING_COLON, "Add missing colon after control structures"
                    elif error_key == "unexpected_eof":
                        return SyntaxErrorType.UNEXPECTED_EOF, "Missing closing parentheses, brackets, or quotes"
                    elif error_key == "invalid_character":
                        return SyntaxErrorType.INVALID_CHARACTER, "Remove invalid characters or fix encoding issues"
                    elif error_key == "parentheses_mismatch":
                        return SyntaxErrorType.PARENTHESES_MISMATCH, "Check for missing or extra parentheses"
                    elif error_key == "print_statement":
                        return SyntaxErrorType.PRINT_STATEMENT, "Convert print statement to function call"
        
        # Fallback classifications
        if "indentation" in error_output_lower:
            return SyntaxErrorType.INDENTATION_SYNTAX, "Fix indentation - use consistent spaces or tabs"
        else:
            return SyntaxErrorType.GENERAL_SYNTAX, "Fix syntax error - check Python syntax rules"
    
    def _extract_line_number(self, error_output: str) -> Optional[int]:
        """Extract line number from error output"""
        line_match = re.search(r'line (\d+)', error_output)
        return int(line_match.group(1)) if line_match else None
    
    def _check_version_compatibility(self, error_output: str) -> Optional[Dict]:
        """Check for Python version compatibility issues"""
        if "print" in error_output.lower() and "invalid syntax" in error_output.lower():
            return {
                "feature": "print statement",
                "required_version": "2.x",
                "current_version": "3.x",
                "suggestion": "Use print() function instead of print statement"
            }
        return None
    
    def apply_syntax_fix(self, file_path: str, error_type: SyntaxErrorType, details: Dict) -> bool:
        """
        Apply the appropriate fix based on error type
        """
        try:
            print(f"DEBUG: Attempting to fix {error_type.value} in {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            print(f"DEBUG: Original content length: {len(content)} chars")
            
            # Apply specific fixes based on error type
            if error_type == SyntaxErrorType.MISSING_COLON:
                print("DEBUG: Applying missing colon fix")
                content = self._fix_missing_colons(content, details)
            
            elif error_type == SyntaxErrorType.PARENTHESES_MISMATCH:
                print("DEBUG: Applying parentheses mismatch fix")
                content = self._fix_parentheses_mismatch(content)
            
            elif error_type == SyntaxErrorType.UNEXPECTED_EOF:
                print("DEBUG: Applying unexpected EOF fix")
                content = self._fix_unexpected_eof(content)
            
            elif error_type == SyntaxErrorType.PRINT_STATEMENT:
                print("DEBUG: Applying print statement fix")
                content = self._fix_print_statements(content)
            
            elif error_type == SyntaxErrorType.BROKEN_KEYWORDS:
                print("DEBUG: Applying broken keywords fix")
                content = self._fix_broken_keywords(content)
            
            elif error_type == SyntaxErrorType.INDENTATION_SYNTAX:
                print("DEBUG: Applying indentation syntax fix")
                content = self._fix_basic_indentation(content)
            
            else:
                print(f"DEBUG: Applying general fixes for {error_type.value}")
                content = self._apply_general_fixes(content, details)
            
            print(f"DEBUG: Fixed content length: {len(content)} chars")
            print(f"DEBUG: Content changed: {content != original_content}")
            
            # Write back if changes were made
            if content != original_content:
                # Create backup first
                self._create_backup(file_path)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"Successfully applied {error_type.value} fix to {file_path}")
                return True
            else:
                print(f"DEBUG: No changes made to content")
                return False
            
        except Exception as e:
            print(f"Failed to fix syntax error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _fix_missing_colons(self, content: str, details: Dict) -> str:
        """Fix missing colons after control structures - IMPROVED VERSION"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('#'):
                continue
            
            # Check each control structure pattern
            for pattern in self.control_structure_patterns:
                match = re.match(pattern, line)
                if match:
                    indent_part = match.group(1)
                    code_part = match.group(2)
                    comment_part = match.group(3) if len(match.groups()) >= 3 and match.group(3) else ""
                    
                    # Check if colon is missing
                    if not code_part.rstrip().endswith(':'):
                        # Add the colon
                        lines[i] = f"{indent_part}{code_part.rstrip()}:{comment_part}"
                        print(f"Fixed missing colon on line {i+1}: {lines[i].strip()}")
                    break
        
        return '\n'.join(lines)
    
    def _fix_parentheses_mismatch(self, content: str) -> str:
        """Basic parentheses balancing"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            open_count = line.count('(')
            close_count = line.count(')')
            
            if open_count > close_count:
                lines[i] = line + ')' * (open_count - close_count)
                print(f"Added {open_count - close_count} closing parentheses to line {i+1}")
            elif close_count > open_count and i > 0:
                lines[i-1] = lines[i-1] + '(' * (close_count - open_count)
                print(f"Added {close_count - open_count} opening parentheses to line {i}")
        
        return '\n'.join(lines)
    
    def _fix_unexpected_eof(self, content: str) -> str:
        """Add missing closing characters"""
        original_content = content
        
        # Fix unmatched quotes
        if content.count('"') % 2 == 1:
            content += '"'
            print("Added missing closing double quote")
        if content.count("'") % 2 == 1:
            content += "'"
            print("Added missing closing single quote")
        
        # Fix unmatched brackets
        bracket_pairs = [('(', ')'), ('[', ']'), ('{', '}')]
        
        for open_char, close_char in bracket_pairs:
            open_count = content.count(open_char)
            close_count = content.count(close_char)
            if open_count > close_count:
                content += close_char * (open_count - close_count)
                print(f"Added {open_count - close_count} closing {close_char}")
        
        return content
    
    def _fix_print_statements(self, content: str) -> str:
        """Convert Python 2 print statements to Python 3 - FIXED VERSION"""
        print("DEBUG: *** USING FIXED VERSION OF _fix_print_statements ***")
        lines = content.split('\n')
        changes_made = False
    
        for i, line in enumerate(lines):
            # Skip comment lines
            if line.strip().startswith('#'):
                continue
            
            if 'print ' in line:
                print(f"DEBUG: Line {i+1} contains 'print ': {line}")
            
            # Check if the actual code part (not comment) already has print()
            code_part = line.split('#')[0]  # Get part before comment
            if 'print(' in code_part:
                print("DEBUG: Code part already has print(), skipping")
                continue
                
            original_line = line
            print(f"DEBUG: Processing line {i+1}: '{original_line}'")
            
            # Split line into code and comment parts
            if '#' in line:
                code_part, comment_part = line.split('#', 1)
                comment_part = '#' + comment_part
            else:
                code_part = line
                comment_part = ""
            
            # Apply fix to code part only
            fixed_code = code_part
            
            # Pattern 1: print "text" or print 'text'
            fixed_code = re.sub(r'\bprint\s+"([^"]*)"', r'print("\1")', fixed_code)
            fixed_code = re.sub(r"\bprint\s+'([^']*)'", r"print('\1')", fixed_code)
            
            # Pattern 2: print variable_or_expression
            fixed_code = re.sub(r'\bprint\s+([^()"\'\n]+)', lambda m: f'print({m.group(1).rstrip()})', fixed_code)
            
            # Reconstruct the line
            new_line = fixed_code + comment_part
            
            if new_line != original_line:
                lines[i] = new_line
                changes_made = True
                print(f"DEBUG: CHANGED line {i+1}")
                print(f"DEBUG: FROM: '{original_line}'")
                print(f"DEBUG: TO:   '{new_line}'")
            else:
                print(f"DEBUG: NO CHANGE made to line {i+1}")
    
        result = '\n'.join(lines)
        print(f"DEBUG: Total changes made: {changes_made}")
    
        return result
    
    def _fix_broken_keywords(self, content: str) -> str:
        """Fix keywords that have been broken with spaces"""
        original_content = content
        for pattern, replacement in self.keyword_fixes.items():
            content = re.sub(pattern, replacement, content)
        
        if content != original_content:
            print("Fixed broken keywords with spaces")
        
        return content
    
    def _fix_basic_indentation(self, content: str) -> str:
        """Apply basic indentation fixes"""
        lines = content.split('\n')
        formatted_lines = []
        
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                # Check if this should be indented
                if any(keyword in line for keyword in ['return ', 'print(', 'pass', '=']):
                    # Look at previous line
                    if formatted_lines and formatted_lines[-1].strip().endswith(':'):
                        line = '    ' + line
                        print(f"Added indentation to line {i+1}")
            
            formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def _apply_general_fixes(self, content: str, details: Dict) -> str:
        """Apply general syntax fixes"""
        original_content = content
        
        # Apply all basic fixes
        content = self._fix_broken_keywords(content)
        content = self._fix_missing_colons(content, details)
        content = self._fix_unexpected_eof(content)
        
        return content
    
    def _create_backup(self, file_path: str) -> None:
        """Create backup of original file"""
        backup_path = f"{file_path}.backup"
        shutil.copy2(file_path, backup_path)
        print(f"Created backup: {backup_path}")
    
    def get_error_name(self) -> str:
        """Return the error name for this handler"""
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
    success = handler.apply_syntax_fix(file_path, error_type, details)
    
    if success:
        print(f"Fixed {error_type.value}: {suggestion}")
    else:
        suggestions = handler.generate_fix_suggestions(error_type)
        print(f"Manual fixes needed: {suggestions}")
"""