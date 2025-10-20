"""
Domain entity: FixResult

Represents the result of attempting to automatically fix a code issue.
This object is immutable to record the final outcome of a fix attempt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Any


@dataclass(frozen=True)
class FixResult:
    """
    Immutable result describing the outcome of a fix attempt.

    Attributes:
    - success: whether the fix was applied successfully
    - fixed_code: resulting code after the fix (if success)
    - original_code: original code before the fix
    - changes: ordered tuple of change descriptors (diff-like dicts)
    - method: short string describing the method used (e.g., "ai_patch", "text_replace")
    - error_message: error details if the fix failed
    """
    success: bool
    fixed_code: Optional[str] = None
    original_code: Optional[str] = None
    changes: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)
    method: Optional[str] = None
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        # If success is True, best-effort validation to ensure we have fixed_code
        if self.success and self.fixed_code is None:
            raise ValueError("fixed_code must be set when success is True")

    def to_dict(self) -> Dict[str, Any]:
        """Return a serializable representation."""
        return {
            "success": self.success,
            "fixed_code": self.fixed_code,
            "original_code": self.original_code,
            "changes": list(self.changes),
            "method": self.method,
            "error_message": self.error_message,
        }

# TODO: Add richer Change objects (instead of plain dicts) if downstream
#       processing requires structured diffs.