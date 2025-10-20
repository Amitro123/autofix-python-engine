from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

class AIServiceInterface(ABC):
    """
    Abstract base class for AI provider adapters.

    Implementations should translate application prompts into provider-specific
    API calls and return normalized results.

    This API includes both synchronous and asynchronous patterns to accommodate
    different providers and hosting models.
    """

    @abstractmethod
    async def generate_text(self, prompt: str, *, max_tokens: int | None = None, **kwargs: Any) -> str:
        """
        Asynchronously generate text from the provider given a prompt.

        Parameters:
        - prompt: input prompt for the model
        - max_tokens: optional token limit
        - kwargs: provider-specific options

        Returns:
        - Generated text (plain string). Higher-level code should convert into domain types.
        """
        raise NotImplementedError

    @abstractmethod
    def generate_text_sync(self, prompt: str, *, max_tokens: int | None = None, **kwargs: Any) -> str:
        """
        Synchronous variant for environments where async usage isn't available.

        Providers may implement either or both methods. Tests should mock both.
        """
        raise NotImplementedError

    # TODO:
    # - Consider adding stream() or iter_tokens() for streaming providers.
    # - Add detailed error wrapping for provider errors (rate limits, timeouts).