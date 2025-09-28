"""
AutoFix Python Engine

A simple, focused tool for automatically fixing common Python errors.
"""

# Handle both relative and absolute imports
try:
    from .python_fixer import PythonFixer
    from .error_parser import ErrorParser, ParsedError
    from .logging_utils import setup_logging, get_logger
    from .autofix_cli_interactive import main as cli_main
    from .constants import (
        ErrorType, 
        SyntaxErrorSubType, 
        FixStatus, 
        MetadataKey,
        MAX_RETRIES,
        DEFAULT_TIMEOUT,
        BACKUP_EXTENSION
    )
except ImportError:
    # Fallback for direct execution
    from python_fixer import PythonFixer
    from autofix.error_parser import ErrorParser, ParsedError
    from logging_utils import setup_logging, get_logger
    from autofix_cli_interactive import main as cli_main
    from constants import (
        ErrorType, 
        SyntaxErrorSubType, 
        FixStatus, 
        MetadataKey,
        MAX_RETRIES,
        DEFAULT_TIMEOUT,
        BACKUP_EXTENSION
    )

__version__ = "1.0.0"

# Public API - what users get when they import autofix
__all__ = [
    # Core functionality
    "PythonFixer",
    "ErrorParser", 
    "ParsedError",
    "cli_main",
    
    # Logging utilities
    "setup_logging",
    "get_logger",
    
    # Constants and Enums
    "ErrorType",
    "SyntaxErrorSubType",
    "FixStatus",
    "MetadataKey",
    
    # Global constants
    "MAX_RETRIES",
    "DEFAULT_TIMEOUT",
    "BACKUP_EXTENSION"
]
