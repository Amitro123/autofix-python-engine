"""
Value object: CodeLocation

Small immutable structure describing a location in source code.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CodeLocation:
    """
    Immutable specification of a source code location.

    - line: 1-based line number (must be >= 1)
    - column: 0-based column index (must be >= 0)
    - file_path: optional filesystem path or logical path
    """
    line: int
    column: int
    file_path: Optional[str] = None

    def __post_init__(self) -> None:
        if self.line < 1:
            raise ValueError("line must be >= 1")
        if self.column < 0:
            raise ValueError("column must be >= 0")

    def __str__(self) -> str:
        path = self.file_path or "<unknown>"
        return f"{path}:{self.line}:{self.column}"

# TODO: Add convenience: from_ast_node, from_traceback, and methods to compute
#       ranges (start/end) for multi-line issues.