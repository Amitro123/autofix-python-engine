"""
Value object: ErrorType

Enumerates the kinds of errors AutoFix understands. Used by handlers,
execution reporting and fix strategies to classify problems.
"""
from __future__ import annotations

from enum import Enum, auto


class ErrorType(Enum):
    """
    Canonical error type enumeration used across the domain.
    """
    SYNTAX_ERROR = auto()
    IMPORT_ERROR = auto()
    MODULE_NOT_FOUND = auto()
    NAME_ERROR = auto()
    TYPE_ERROR = auto()
    VALUE_ERROR = auto()
    INDEX_ERROR = auto()
    KEY_ERROR = auto()
    ZERO_DIVISION_ERROR = auto()
    FILE_NOT_FOUND = auto()
    UNKNOWN = auto()

    def __str__(self) -> str:
        return self.name

# TODO: If needed, add mapping helpers (from_exception, from_pylint_code, ...)
#       to translate external error forms into this enum.