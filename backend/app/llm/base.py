"""The interface every AI provider implements, so providers can be swapped without touching the rest."""

from typing import Protocol


class ProviderError(Exception):
    """The AI provider could not produce a reply. The message is safe to log."""


class LLMProvider(Protocol):
    name: str

    def generate(self, system: str, user: str, max_tokens: int) -> str:
        """Return the model's reply text. Raises ProviderError on any failure."""
        ...