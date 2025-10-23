# autofix_core/shared/__init__.py
"""Shared utilities and constants for AutoFix Core"""

from .core.error_parser import ErrorParser, ParsedError
from .helpers.logging_utils import setup_logging, get_logger
from .constants import (
    ErrorType,
    SyntaxErrorSubType,
    FixStatus,
    MetadataKey,
    MAX_RETRIES,
    DEFAULT_TIMEOUT,
    BACKUP_EXTENSION,
)

__version__ = '1.0.0'

__all__ = [
    'ErrorParser',
    'ParsedError',
    'setup_logging',
    'get_logger',
    'ErrorType',
    'SyntaxErrorSubType',
    'FixStatus',
    'MetadataKey',
    'MAX_RETRIES',
    'DEFAULT_TIMEOUT',
    'BACKUP_EXTENSION',
]