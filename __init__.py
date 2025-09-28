"""
AutoFix - Intelligent Python Error Fixer

A simple, focused tool for automatically fixing common Python errors.
"""

from python_fixer import PythonFixer
from autofix.error_parser import ErrorParser, ParsedError
from logging_utils import setup_logging, get_logger

__version__ = "1.0.0"
__all__ = ["PythonFixer", "ErrorParser", "ParsedError", "AutoFixCLI"]