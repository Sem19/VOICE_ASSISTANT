from abc import ABC, abstractmethod


class LLMServiceError(Exception):
    """Raised when the LLM provider returns an error response."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class LLMServiceUnavailableError(LLMServiceError):
    """Raised when the LLM provider cannot be reached."""

    def __init__(self, message: str = "LLM service is unavailable") -> None:
        super().__init__(message, status_code=503)


class LLMService(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict[str, str]]) -> str:
        """Send a conversation history and return the assistant reply."""
