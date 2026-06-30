import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_chat_service
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import ChatService
from app.services.llm.base import LLMServiceError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    try:
        response, session_id = await chat_service.send_message(
            message=request.message,
            session_id=request.session_id,
        )
    except LLMServiceError as exc:
        logger.error("Chat request failed: %s", exc.message)
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc

    return ChatResponse(response=response, session_id=session_id)
