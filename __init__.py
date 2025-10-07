"""
AutoFix Python Engine

A simple, focused tool for automatically fixing common Python errors.
"""

from autofix.python_fixer import PythonFixer
from autofix.core.error_parser import ErrorParser, ParsedError
from autofix.helpers.logging_utils import setup_logging, get_logger
from autofix.cli.autofix_cli_interactive import main as cli_main
from autofix.constants import (
    ErrorType,
    SyntaxErrorSubType,
    FixStatus,
    MetadataKey,
    MAX_RETRIES,
    DEFAULT_TIMEOUT,
    BACKUP_EXTENSION,
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