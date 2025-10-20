from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

# Forward reference to domain FixResult (to be implemented)
# from autofix_core.domain.entities import FixResult

class HandlerInterface(ABC):
    """
    Abstract base class for error handlers.

    Each concrete handler decides whether it can handle a given error and,
    when applicable, produces an automated fix (or instructions) as a domain
    FixResult.

    Typical handler responsibilities:
    - Inspect exception or diagnostics
    - Optionally produce modifications or a fix plan
    - Report metadata (severity, confidence)
    """

    @abstractmethod
    def can_handle(self, error: Exception, *, context: dict[str, Any] | None = None) -> bool:
        """
        Return True if this handler is capable of handling the given error context.

        Parameters:
        - error: the raised Exception or diagnostic object
        - context: optional contextual metadata (file path, traceback, AST, etc.)
        """
        raise NotImplementedError

    @abstractmethod
    def handle(self, error: Exception, *, context: dict[str, Any] | None = None) -> Any:
        """
        Attempt to produce a fix for the provided error.

        Returns:
        - A domain FixResult (or a serializable placeholder until FixResult exists).

        Raise:
        - Handler-specific exceptions or return structured failure results.
        """
        raise NotImplementedError

    # TODO:
    # - Define FixResult domain entity and update return type annotation.
    # - Consider adding priority/ordering metadata on handlers.