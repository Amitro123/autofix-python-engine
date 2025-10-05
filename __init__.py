"""
AutoFix Python Engine

A simple, focused tool for automatically fixing common Python errors.
"""

from python_fixer import PythonFixer
from error_parser import ErrorParser, ParsedError
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

__all__ = [
    "PythonFixer",
    "ErrorParser", 
    "ParsedError",
    "cli_main",
    "setup_logging",
    "get_logger",
    "ErrorType",
    "SyntaxErrorSubType",
    "FixStatus",
    "MetadataKey",
    "MAX_RETRIES",
    "DEFAULT_TIMEOUT",
    "BACKUP_EXTENSION"
]