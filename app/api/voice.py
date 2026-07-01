import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import get_voice_pipeline_service
from app.api.transcribe import ALLOWED_EXTENSIONS
from app.schemas.voice import LatencyMetrics, VoiceDebugResponse
from app.services.llm.base import LLMServiceError
from app.services.stt.base import STTServiceError
from app.services.tts.base import TTSServiceError
from app.services.voice.pipeline import VoicePipelineResult, VoicePipelineService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["voice"])


def _voice_response_headers(result: VoicePipelineResult) -> dict[str, str]:
    return {
        "X-End-Call": "true" if result.end_call else "false",
        "X-Call-Id": result.call_id or "",
        "X-Turn-Number": str(result.turn_number or 0),
        "X-Session-Id": result.session_id or "",
    }


@router.post("/voice", response_model=None)
async def voice(
    file: UploadFile = File(...),
    session_id: str | None = Form(None),
    call_id: str | None = Form(None),
    turn_number: int | None = Form(None),
    return_debug: bool = Form(False),
    pipeline: VoicePipelineService = Depends(get_voice_pipeline_service),
) -> FileResponse | VoiceDebugResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: wav, mp3, m4a, flac",
        )

    temp_path: str | None = None
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty audio file")

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            temp_path = tmp.name
            tmp.write(content)

        try:
            result = await pipeline.process(
                file_path=temp_path,
                session_id=session_id,
                call_id=call_id,
                turn_number=turn_number,
                filename=file.filename,
            )
        except STTServiceError as exc:
            logger.error(
                "Voice request failed during STT call_id=%s turn=%s: %s",
                call_id,
                turn_number,
                exc,
            )
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except LLMServiceError as exc:
            logger.error(
                "Voice request failed during LLM call_id=%s turn=%s: %s",
                call_id,
                turn_number,
                exc.message,
            )
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
        except TTSServiceError as exc:
            logger.error(
                "Voice request failed during TTS call_id=%s turn=%s: %s",
                call_id,
                turn_number,
                exc.message,
            )
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

        if return_debug:
            return VoiceDebugResponse(
                transcription=result.transcription,
                llm_response=result.llm_response,
                audio_file_path=str(result.audio_path),
                latency=LatencyMetrics(
                    stt_ms=result.latency.stt_ms,
                    llm_ms=result.latency.llm_ms,
                    tts_ms=result.latency.tts_ms,
                    total_ms=result.latency.total_ms,
                ),
                end_call=result.end_call,
                call_id=result.call_id,
                turn_number=result.turn_number,
                session_id=result.session_id,
            )

        return FileResponse(
            path=result.audio_path,
            media_type="audio/wav",
            filename=result.audio_path.name,
            headers=_voice_response_headers(result),
        )
    finally:
        if temp_path is not None:
            Path(temp_path).unlink(missing_ok=True)
