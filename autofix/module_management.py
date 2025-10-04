#!/usr/bin/env python3
"""
DEPRECATED: This module has been moved to handlers/module_not_found_handler.py

All functionality is now available in the unified handler:
- ModuleCreator -> handlers.module_not_found_handler.ModuleCreator
- PackageInstaller -> handlers.module_not_found_handler.PackageInstaller

This file will be removed in a future version.
"""

import warnings

warnings.warn(
    "module_management is deprecated. Use handlers.module_not_found_handler instead.",
    DeprecationWarning,
    stacklevel=2
)

# Forward imports for backward compatibility
from .handlers.module_not_found_handler import (
    ModuleCreator,
    PackageInstaller
)

__all__ = ['ModuleCreator', 'PackageInstaller']
