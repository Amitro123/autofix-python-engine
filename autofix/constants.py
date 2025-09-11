from enum import Enum, auto
from typing import Final

#todo add more logic!!
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
    
    @classmethod
    def from_string(cls, error_string: str):
        """Convert error type string to ErrorType enum"""
        error_map = {
            "ModuleNotFoundError": cls.MODULE_NOT_FOUND,
            "ImportError": cls.IMPORT_ERROR,
            "NameError": cls.NAME_ERROR,
            "AttributeError": cls.ATTRIBUTE_ERROR,
            "SyntaxError": cls.SYNTAX_ERROR,
            "IndexError": cls.INDEX_ERROR,
            "TypeError": cls.TYPE_ERROR,
            "IndentationError": cls.INDENTATION_ERROR,
        }
        return error_map.get(error_string)
    
    def to_string(self) -> str:
        """Convert ErrorType back to Python error string"""
        string_map = {
            self.MODULE_NOT_FOUND: "ModuleNotFoundError",
            self.IMPORT_ERROR: "ImportError", 
            self.NAME_ERROR: "NameError",
            self.ATTRIBUTE_ERROR: "AttributeError",
            self.SYNTAX_ERROR: "SyntaxError",
            self.INDEX_ERROR: "IndexError",
            self.TYPE_ERROR: "TypeError",
            self.INDENTATION_ERROR: "IndentationError",
        }
        return string_map.get(self, "UnknownError")


# ========== SYNTAX ERROR SUBTYPES ==========
class SyntaxErrorSubType(Enum):
    """Subtypes of syntax errors for detailed classification"""
    MISSING_COLON = "missing_colon"
    INCONSISTENT_INDENTATION = "inconsistent_indentation"
    UNEXPECTED_INDENT = "unexpected_indent"
    EMPTY_LIST_POP = "empty_list_pop"
    PARENTHESES_MISMATCH = "parentheses_mismatch"
    UNEXPECTED_EOF = "unexpected_eof"
    MISSING_INDENTATION = "missing_indentation"

# ========== REGEX PATTERNS ==========
class RegexPatterns:
    """Centralized regex patterns for error fixes"""



# ========== FIX STATUS ==========
class FixStatus(Enum):
    """Status codes for fix operations"""
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELED = "canceled"
    FIX_APPLIED = "fix_applied"
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
