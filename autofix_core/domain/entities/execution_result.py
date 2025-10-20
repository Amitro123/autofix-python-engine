"""
Domain entity: ExecutionResult

Represents the outcome of executing code in a sandbox/debugger. This object is
mutable because runtime execution may populate variables post-construction in
some debugger flows.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any

# Value object reference
from autofix_core.domain.value_objects.error_type import ErrorType


@dataclass
class ExecutionResult:
    """
    Mutable container for results of executing code.

    Attributes:
    - success: Whether execution completed without raising a fatal error
    - output: Captured stdout/stderr output (if any)
    - error: Error message / traceback (if any)
    - error_type: Categorized error type (if error occurred)
    - variables: Mapping of variable names to their runtime values (sandboxed)
    - execution_time: Execution duration in seconds (float), optional
    - timeout: True if execution was aborted due to timeout
    """
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[ErrorType] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    execution_time: Optional[float] = None
    timeout: bool = False

    def __post_init__(self) -> None:
        if self.execution_time is not None:
            if self.execution_time < 0:
                raise ValueError("execution_time must be non-negative")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ExecutionResult to a serializable dict for transport/logging.
        Note: variables may contain non-serializable values depending on debugger.
        """
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "error_type": self.error_type.name if self.error_type is not None else None,
            "variables": self.variables,
            "execution_time": self.execution_time,
            "timeout": self.timeout,
        }

# TODO: Consider adding helper methods for safe variable serialization and
#       merging partial execution results from multi-step debugging flows.