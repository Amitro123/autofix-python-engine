from enum import Enum, auto

class ErrorType(Enum):
    """Enumeration of error types that AutoFix can handle"""
    MODULE_NOT_FOUND = auto()
    IMPORT_ERROR = auto() 
    NAME_ERROR = auto()
    ATTRIBUTE_ERROR = auto()
    SYNTAX_ERROR = auto()
    INDEX_ERROR = auto()
    
    @classmethod
    def from_string(cls, error_string: str):
        """Convert error type string to ErrorType enum"""
        # Map common error strings to enum values
        error_map = {
            "ModuleNotFoundError": cls.MODULE_NOT_FOUND,
            "ImportError": cls.IMPORT_ERROR,
            "NameError": cls.NAME_ERROR,
            "AttributeError": cls.ATTRIBUTE_ERROR,
            "SyntaxError": cls.SYNTAX_ERROR,
            "IndexError": cls.INDEX_ERROR,
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
        }
        
        return string_map.get(self, "UnknownError")
