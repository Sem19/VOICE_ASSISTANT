from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str
    duration_seconds: float


class STTServiceError(Exception):
    """Raised when speech-to-text processing fails."""


class UnsupportedAudioFormatError(STTServiceError):
    """Raised when the audio file format is not supported."""


class STTService(ABC):
    @abstractmethod
    def transcribe(self, file_path: str) -> TranscriptionResult:
        """Transcribe an audio file and return the recognized text."""
