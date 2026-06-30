import logging
import time
import uuid
import wave
from pathlib import Path

from app.services.tts.base import TTSModelNotFoundError, TTSService, TTSServiceError

logger = logging.getLogger(__name__)


class PiperTTSService(TTSService):
    def __init__(
        self,
        model_path: str,
        config_path: str,
        output_dir: str,
    ) -> None:
        self._model_path = Path(model_path)
        self._config_path = Path(config_path)
        self._output_dir = Path(output_dir)
        self._voice = None

    def _validate_model_files(self) -> None:
        if not self._model_path.is_file():
            raise TTSModelNotFoundError(str(self._model_path))
        if not self._config_path.is_file():
            raise TTSModelNotFoundError(str(self._config_path))

    def _load_voice(self):
        if self._voice is None:
            self._validate_model_files()
            from piper import PiperVoice

            logger.info("Loading Piper voice model from %s", self._model_path)
            self._voice = PiperVoice.load(
                str(self._model_path),
                config_path=str(self._config_path),
            )
        return self._voice

    def synthesize(self, text: str) -> Path:
        start = time.perf_counter()
        self._output_dir.mkdir(parents=True, exist_ok=True)

        output_path = self._output_dir / f"{uuid.uuid4()}.wav"

        try:
            voice = self._load_voice()
            with wave.open(str(output_path), "wb") as wav_file:
                voice.synthesize_wav(text, wav_file)
        except TTSModelNotFoundError:
            raise
        except Exception as exc:
            logger.error("Piper synthesis failed: %s", exc)
            if output_path.exists():
                output_path.unlink(missing_ok=True)
            raise TTSServiceError(f"Speech synthesis failed: {exc}") from exc

        elapsed = time.perf_counter() - start
        logger.info(
            "Speech synthesis completed in %.2fs (%d characters, output: %s)",
            elapsed,
            len(text),
            output_path.name,
        )
        return output_path
