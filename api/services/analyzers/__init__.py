"""
DEPRECATED: Analyzers have been moved to autofix_core.infrastructure.analyzers

This module provides backwards compatibility shims.
Import from the new location:
    from autofix_core.infrastructure.analyzers import PylintAnalyzer, BanditAnalyzer, RadonAnalyzer
"""
import warnings

# Import from new locations
from autofix_core.infrastructure.analyzers.pylint_analyzer import PylintAnalyzer
from autofix_core.infrastructure.analyzers.bandit_analyzer import BanditAnalyzer
from autofix_core.infrastructure.analyzers.radon_analyzer import RadonAnalyzer

# Show deprecation warning
warnings.warn(
    "Importing analyzers from api.services.analyzers is deprecated. "
    "Use 'from autofix_core.infrastructure.analyzers import PylintAnalyzer' instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    "PylintAnalyzer",
    "BanditAnalyzer", 
    "RadonAnalyzer"
]
