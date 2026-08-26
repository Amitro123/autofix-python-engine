from enum import Enum, auto
from re import S
from typing import Final, List, Dict, Optional
import logging

# ========== ERROR TYPES ==========
class ErrorType(Enum):
    """Enumeration of error types that AutoFix can handle"""
    MODULE_NOT_FOUND = auto()
    IMPORT_ERROR = auto()
    NAME_ERROR = auto()
    ATTRIBUTE_ERROR = auto()
    SYNTAX_ERROR = auto()
    INDEX_ERROR = auto()
    TYPE_ERROR = auto()
    INDENTATION_ERROR = auto()
    TAB_ERROR = auto()
    UNKNOWN_ERROR = auto()
    GENERAL_SYNTAX = auto()
    KEY_ERROR = auto()
    ZERO_DIVISION_ERROR = auto()
    FILE_NOT_FOUND = auto()
    VALUE_ERROR = auto()

    @classmethod
    def from_string(cls, error_string: str):
        """Convert error type string to ErrorType enum"""
        return _ERROR_TYPE_FROM_STRING.get(error_string)

    def to_string(self) -> str:
        """Convert ErrorType back to Python error string"""
        return _ERROR_TYPE_TO_STRING.get(self, "UnknownError")


# Module-level so from_string()/to_string() don't rebuild these dicts on
# every call -- built once at import time instead.
_ERROR_TYPE_FROM_STRING = {
    "ModuleNotFoundError": ErrorType.MODULE_NOT_FOUND,
    "ImportError": ErrorType.IMPORT_ERROR,
    "NameError": ErrorType.NAME_ERROR,
    "AttributeError": ErrorType.ATTRIBUTE_ERROR,
    "SyntaxError": ErrorType.SYNTAX_ERROR,
    "IndexError": ErrorType.INDEX_ERROR,
    "TypeError": ErrorType.TYPE_ERROR,
    "IndentationError": ErrorType.INDENTATION_ERROR,
    "TabError": ErrorType.TAB_ERROR,
    "UnknownError": ErrorType.UNKNOWN_ERROR,
    "general_syntax": ErrorType.GENERAL_SYNTAX,
    "GeneralSyntax": ErrorType.GENERAL_SYNTAX,
    "missing_colon": ErrorType.GENERAL_SYNTAX,
    "KeyError": ErrorType.KEY_ERROR,
    "ZeroDivisionError": ErrorType.ZERO_DIVISION_ERROR,
    "FileNotFoundError": ErrorType.FILE_NOT_FOUND,
    "FileNotFound": ErrorType.FILE_NOT_FOUND,
    "ValueError": ErrorType.VALUE_ERROR,
}

_ERROR_TYPE_TO_STRING = {
    ErrorType.MODULE_NOT_FOUND: "ModuleNotFoundError",
    ErrorType.IMPORT_ERROR: "ImportError",
    ErrorType.NAME_ERROR: "NameError",
    ErrorType.ATTRIBUTE_ERROR: "AttributeError",
    ErrorType.SYNTAX_ERROR: "SyntaxError",
    ErrorType.INDEX_ERROR: "IndexError",
    ErrorType.TYPE_ERROR: "TypeError",
    ErrorType.INDENTATION_ERROR: "IndentationError",
    ErrorType.TAB_ERROR: "TabError",
    ErrorType.UNKNOWN_ERROR: "UnknownError",
    ErrorType.GENERAL_SYNTAX: "general_syntax",
    ErrorType.KEY_ERROR: "KeyError",
    ErrorType.ZERO_DIVISION_ERROR: "ZeroDivisionError",
    ErrorType.FILE_NOT_FOUND: "FileNotFoundError",
    ErrorType.VALUE_ERROR: "ValueError",
}

# ========== SYNTAX ERROR TYPES ==========
class SyntaxErrorType(Enum):
    """Enumeration of different syntax error types"""
    MISSING_COLON = "missing_colon"
    PARENTHESES_MISMATCH = "parentheses_mismatch"
    UNEXPECTED_EOF = "unexpected_eof"
    INVALID_CHARACTER = "invalid_character"
    PRINT_STATEMENT = "print_statement"
    BROKEN_KEYWORDS = "broken_keywords"
    VERSION_COMPATIBILITY = "version_compatibility"
    GENERAL_SYNTAX = "general_syntax"
    INDENTATION_ERROR = "indentation_error"


# ========== SYNTAX ERROR SUBTYPES ==========
class SyntaxErrorSubType(Enum):
    """Subtypes of syntax errors for detailed classification"""
    MISSING_COLON = "missing_colon"
    INCONSISTENT_INDENTATION = "inconsistent_indentation"
    UNEXPECTED_INDENT = "unexpected_indent"
    EMPTY_LIST_POPERROR = "empty_list_pop"
    PARENTHESES_MISMATCH = "parentheses_mismatch"
    UNEXPECTED_EOF = "unexpected_eof"
    MISSING_INDENTATION = "missing_indentation"
    SYNTAX_UNSUPPORTED_OPERAND = "unsupported_operand"
    NEGATIVE_INDEXING = "negative_indexing"

# ========== REGEX PATTERNS ==========
class RegexPatterns:
    """Centralized regex patterns for error fixes"""
    MODULE_NAME = r"No module named ['\"]([^'\"]+)['\"]"
    # group(1) = imported name, group(2) = module it was imported from.
    # Accepts both quote styles (some call sites only handled single
    # quotes and had silently diverged from this one).
    CANNOT_IMPORT_NAME = r"cannot import name ['\"]([^'\"]+)['\"] from ['\"]([^'\"]+)['\"]"
    NAME_NOT_DEFINED = r"name '([^']+)' is not defined"
    STRING_PLUS_NUMBER_1 = r'(["\'][^"\']*["\'])\s*\+\s*(\d+)'
    STRING_PLUS_NUMBER_2 = r'(\d+)\s*\+\s*(["\'][^"\']*["\'])'
    STRING_PLUS_NUMBER_3 = r'(\w+)\s*\+\s*(\d+)'
    LIST_PLUS_STRING = r'\[\w+\]\s*\+\s*(["\'][^"\']*["\'])'
    FOR_IN_VARIABLE = r'for\s+(\w+)\s+in\s+(\w+)(?!\[)'
    INDEX_ACCESS = r'(\w+)\[(\d+)\]'
    NEGATIVE_INDEXING = r'(\w+)\[(-?\d+)\]'
    EMPTY_LIST_POP = r'(\w+)\.pop\(\)'
    LINE_NUMBER = r'line (\d+)'

    # Syntax Error Detection patterns (for classification only)
    SYNTAX_MISSING_COLON = r"expected ':'"
    SYNTAX_UNEXPECTED_EOF = r"unexpected EOF"
    SYNTAX_INVALID_CHARACTER = r"invalid character"
    SYNTAX_PARENTHESES_MISMATCH = r"[()]\s*(invalid syntax|unexpected)"



# ========== FIX STATUS ==========
class FixStatus(Enum):
    """Status codes for fix operations"""
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELED = "canceled"
    FIX_APPLIED = "fix_applied"
    FIX_FAILED = "fix_failed"
    UNSUPPORTED_ERROR = "unsupported_error"
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"
    UNKNOWN = "unknown"

# ========== METADATA KEYS ==========
class MetadataKey(Enum):
    """Keys for metadata dictionaries"""
    ERROR_OUTPUT = "error_output"
    ORIGINAL_ERROR = "original_error"
    LINE_NUMBER = "line_number"
    MODULE_NAME = "module_name"
    FUNCTION_NAME = "function_name"

# ========== GLOBAL CONSTANTS ==========
MAX_RETRIES: Final[int] = 3
DEFAULT_TIMEOUT: Final[int] = 30
BACKUP_EXTENSION: Final[str] = ".autofix.bak"

# ========== ENVIRONMENT VARIABLES ==========

class EnvironmentVariables:
    DEFAULT_APP_ID: Final[str] = "autofix-default-app"

# ========== ERROR MESSAGE PATTERNS ==========
class ErrorMessagePatterns:
    UNSUPPORTED_OPERAND = ["unsupported operand type", "can only concatenate"]
    MISSING_ARGUMENT = ["missing", "required positional argument"]
    NOT_ITERABLE = "not iterable"
    NOT_SUBSCRIPTABLE = "not subscriptable"
    NOT_CALLABLE = "not callable"
    POSITIONAL_ARGUMENT = "positional argument"

# ========== VALIDATION PATTERNS ==========
class ValidationPatterns:
    """Patterns for validation operations"""
    TEST_MODULE_PATTERNS: Final[List[str]] = [
        r'test[_\d]*',
        r'example[_\d]*',
        r'demo[_\d]*',
        r'placeholder[_\d]*',
        r'nonexistent[_\d]*',
        r'non_existent[_\d]*',
        r'fake[_\d]*',
        r'dummy[_\d]*',
        r'mock[_\d]*',
        r'invalid[_\d]*',
        r'sample[_\d]*'
    ]

    TEST_MODULE_INDICATORS: Final[List[str]] = [
        "non_existent", "nonexistent", "fake", "test", 
        "dummy", "placeholder", "example", "sample", "mock", "invalid"
    ]



