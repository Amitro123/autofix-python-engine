#!/usr/bin/env python3
"""
DEPRECATED: This module has been moved to handlers/module_not_found_handler.py

ModuleValidation is now available at:
- handlers.module_not_found_handler.ModuleValidation

This file will be removed in a future version.
"""

import warnings

warnings.warn(
    "utils.ModuleValidation is deprecated. Use handlers.module_not_found_handler.ModuleValidation instead.",
    DeprecationWarning,
    stacklevel=2
)

# Forward import for backward compatibility
from ..handlers.module_not_found_handler import ModuleValidation

__all__ = ['ModuleValidation']
