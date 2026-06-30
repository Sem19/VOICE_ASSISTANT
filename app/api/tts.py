import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import get_tts_service
from app.schemas.tts import TTSRequest
from app.services.tts.base import TTSService, TTSServiceError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tts"])


@router.post("/tts")
async def synthesize_speech(
    request: TTSRequest,
    tts_service: TTSService = Depends(get_tts_service),
) -> FileResponse:
    try:
        logger.info("Synthesizing speech for %d characters", len(request.text))
        output_path = await asyncio.to_thread(tts_service.synthesize, request.text)
    except TTSServiceError as exc:
        logger.error("TTS request failed: %s", exc.message)
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc

    return FileResponse(
        path=output_path,
        media_type="audio/wav",
        filename=output_path.name,
    )
