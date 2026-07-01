from functools import lru_cache

from app.core.config import settings
from app.services.chat import ChatService
from app.services.llm.base import LLMService
from app.services.llm.ollama import OllamaService
from app.services.stt.base import STTService
from app.services.stt.faster_whisper import FasterWhisperSTTService
from app.services.tts.base import TTSService
from app.services.tts.piper import PiperTTSService
from app.services.voice.pipeline import VoicePipelineService


@lru_cache
def get_llm_service() -> LLMService:
    return OllamaService(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL,
    )


@lru_cache
def get_chat_service() -> ChatService:
    return ChatService(llm=get_llm_service())


@lru_cache
def get_stt_service() -> STTService:
    return FasterWhisperSTTService(
        model_size=settings.STT_MODEL_SIZE,
        device=settings.STT_DEVICE,
        compute_type=settings.STT_COMPUTE_TYPE,
        language=settings.STT_LANGUAGE,
    )


@lru_cache
def get_tts_service() -> TTSService:
    if settings.TTS_PROVIDER == "piper":
        return PiperTTSService(
            model_path=settings.PIPER_MODEL_PATH,
            config_path=settings.PIPER_CONFIG_PATH,
            output_dir=settings.TTS_OUTPUT_DIR,
        )
    raise ValueError(f"Unsupported TTS provider: {settings.TTS_PROVIDER}")


@lru_cache
def get_voice_pipeline_service() -> VoicePipelineService:
    return VoicePipelineService(
        stt=get_stt_service(),
        chat=get_chat_service(),
        tts=get_tts_service(),
    )
