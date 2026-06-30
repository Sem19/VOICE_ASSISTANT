import logging
import time

from app.services.stt.base import STTService, STTServiceError, TranscriptionResult

logger = logging.getLogger(__name__)


class FasterWhisperSTTService(STTService):
    def __init__(
        self,
        model_size: str,
        device: str,
        compute_type: str,
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model = None

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            logger.info(
                "Loading faster-whisper model size=%s device=%s compute_type=%s",
                self._model_size,
                self._device,
                self._compute_type,
            )
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
        return self._model

    def transcribe(self, file_path: str) -> TranscriptionResult:
        start = time.perf_counter()

        try:
            model = self._load_model()
            segments, info = model.transcribe(file_path)
            text = " ".join(segment.text.strip() for segment in segments).strip()
        except Exception as exc:
            logger.error("Transcription failed for %s: %s", file_path, exc)
            raise STTServiceError(f"Transcription failed: {exc}") from exc

        elapsed = time.perf_counter() - start
        logger.info(
            "Transcription completed in %.2fs (audio duration: %.2fs, language: %s)",
            elapsed,
            info.duration,
            info.language,
        )

        return TranscriptionResult(
            text=text,
            language=info.language,
            duration_seconds=round(info.duration, 2),
        )
