import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.services.chat import ChatService
from app.services.llm.base import LLMServiceError
from app.services.stt.base import STTService, STTServiceError
from app.services.tts.base import TTSService, TTSServiceError
from app.services.voice.constants import SILENCE_PROMPT
from app.services.voice.goodbye import is_goodbye

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
    end_call: bool = False
    call_id: str | None = None
    turn_number: int | None = None
    session_id: str | None = None


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
        call_id: str | None = None,
        turn_number: int | None = None,
        filename: str | None = None,
    ) -> VoicePipelineResult:
        total_start = time.perf_counter()

        logger.info(
            "Starting voice pipeline call_id=%s turn=%s session_id=%s file=%s",
            call_id,
            turn_number,
            session_id,
            filename or file_path,
        )

        stt_start = time.perf_counter()
        try:
            transcription = await asyncio.to_thread(self._stt.transcribe, file_path)
        except STTServiceError:
            logger.error(
                "Voice pipeline STT stage failed call_id=%s turn=%s",
                call_id,
                turn_number,
            )
            raise
        stt_ms = int((time.perf_counter() - stt_start) * 1000)

        transcribed_text = transcription.text.strip()
        end_call = is_goodbye(transcribed_text)
        if turn_number is not None and turn_number >= settings.VOICE_MAX_TURNS:
            end_call = True

        llm_start = time.perf_counter()
        if not transcribed_text:
            logger.warning(
                "Empty transcription call_id=%s turn=%s session_id=%s",
                call_id,
                turn_number,
                session_id,
            )
            llm_response = SILENCE_PROMPT
            resolved_session_id = session_id
            llm_ms = 0
        else:
            try:
                llm_response, resolved_session_id = await self._chat.send_message(
                    message=transcription.text,
                    session_id=session_id,
                )
            except LLMServiceError:
                logger.error(
                    "Voice pipeline LLM stage failed call_id=%s turn=%s",
                    call_id,
                    turn_number,
                )
                raise
            llm_ms = int((time.perf_counter() - llm_start) * 1000)

        logger.info(
            "Voice turn processed call_id=%s turn=%s session_id=%s "
            "transcription=%r end_call=%s llm_chars=%d",
            call_id,
            turn_number,
            resolved_session_id,
            transcribed_text,
            end_call,
            len(llm_response),
        )

        tts_start = time.perf_counter()
        try:
            audio_path = await asyncio.to_thread(self._tts.synthesize, llm_response)
        except TTSServiceError:
            logger.error(
                "Voice pipeline TTS stage failed call_id=%s turn=%s",
                call_id,
                turn_number,
            )
            raise
        tts_ms = int((time.perf_counter() - tts_start) * 1000)

        total_ms = int((time.perf_counter() - total_start) * 1000)

        logger.info(
            "Voice pipeline completed call_id=%s turn=%s session_id=%s "
            "audio=%s stt_ms=%d llm_ms=%d tts_ms=%d total_ms=%d end_call=%s",
            call_id,
            turn_number,
            resolved_session_id,
            audio_path,
            stt_ms,
            llm_ms,
            tts_ms,
            total_ms,
            end_call,
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
            end_call=end_call,
            call_id=call_id,
            turn_number=turn_number,
            session_id=resolved_session_id,
        )
