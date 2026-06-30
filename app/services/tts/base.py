from abc import ABC, abstractmethod
from pathlib import Path


class TTSServiceError(Exception):
    """Raised when text-to-speech processing fails."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class TTSModelNotFoundError(TTSServiceError):
    """Raised when the TTS model files are missing."""

    def __init__(self, path: str) -> None:
        super().__init__(f"TTS model not found: {path}", status_code=503)


class TTSService(ABC):
    @abstractmethod
    def synthesize(self, text: str) -> Path:
        """Synthesize speech from text and return the path to a WAV file."""
