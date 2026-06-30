import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from app.services.chat import ChatService
from app.services.llm.base import LLMServiceError
from app.services.stt.base import STTService, STTServiceError
from app.services.tts.base import TTSService, TTSServiceError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VoicePipelineLatency:
    stt_ms: int
    llm_ms: int
    tts_ms: int
    total_ms: int


@dataclass(frozen=True)
class VoicePipelineResult:
    transcription: str
    llm_response: str
    audio_path: Path
    latency: VoicePipelineLatency


class VoicePipelineService:
    def __init__(
        self,
        stt: STTService,
        chat: ChatService,
        tts: TTSService,
    ) -> None:
        self._stt = stt
        self._chat = chat
        self._tts = tts

    async def process(
        self,
        file_path: str,
        session_id: str | None = None,
        filename: str | None = None,
    ) -> VoicePipelineResult:
        total_start = time.perf_counter()

        logger.info("Starting voice pipeline for file: %s", filename or file_path)

        stt_start = time.perf_counter()
        try:
            transcription = await asyncio.to_thread(self._stt.transcribe, file_path)
        except STTServiceError:
            logger.error("Voice pipeline STT stage failed")
            raise
        stt_ms = int((time.perf_counter() - stt_start) * 1000)

        logger.info("Transcription: %s", transcription.text)

        llm_start = time.perf_counter()
        try:
            llm_response, _session_id = await self._chat.send_message(
                message=transcription.text,
                session_id=session_id,
            )
        except LLMServiceError:
            logger.error("Voice pipeline LLM stage failed")
            raise
        llm_ms = int((time.perf_counter() - llm_start) * 1000)

        logger.info("LLM response length: %d characters", len(llm_response))

        tts_start = time.perf_counter()
        try:
            audio_path = await asyncio.to_thread(self._tts.synthesize, llm_response)
        except TTSServiceError:
            logger.error("Voice pipeline TTS stage failed")
            raise
        tts_ms = int((time.perf_counter() - tts_start) * 1000)

        total_ms = int((time.perf_counter() - total_start) * 1000)

        logger.info(
            "Voice pipeline completed: audio=%s stt_ms=%d llm_ms=%d tts_ms=%d total_ms=%d",
            audio_path,
            stt_ms,
            llm_ms,
            tts_ms,
            total_ms,
        )

        return VoicePipelineResult(
            transcription=transcription.text,
            llm_response=llm_response,
            audio_path=audio_path,
            latency=VoicePipelineLatency(
                stt_ms=stt_ms,
                llm_ms=llm_ms,
                tts_ms=tts_ms,
                total_ms=total_ms,
            ),
        )
