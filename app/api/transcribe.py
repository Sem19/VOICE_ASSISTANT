import asyncio
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_stt_service
from app.schemas.transcription import TranscriptionResponse
from app.services.stt.base import STTService, STTServiceError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["transcription"])

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac"}


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(
    file: UploadFile = File(...),
    stt_service: STTService = Depends(get_stt_service),
) -> TranscriptionResponse:
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

        logger.info("Transcribing uploaded file: %s", file.filename)
        result = await asyncio.to_thread(stt_service.transcribe, temp_path)

        return TranscriptionResponse(
            text=result.text,
            language=result.language,
            duration_seconds=result.duration_seconds,
        )
    except STTServiceError as exc:
        logger.error("Transcription request failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if temp_path is not None:
            Path(temp_path).unlink(missing_ok=True)
