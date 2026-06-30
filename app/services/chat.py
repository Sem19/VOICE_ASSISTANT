import uuid

from app.services.llm.base import LLMService, LLMServiceError


class ChatService:
    def __init__(self, llm: LLMService) -> None:
        self._llm = llm
        self._sessions: dict[str, list[dict[str, str]]] = {}

    async def send_message(
        self,
        message: str,
        session_id: str | None = None,
    ) -> tuple[str, str]:
        sid = session_id or str(uuid.uuid4())
        history = self._sessions.setdefault(sid, [])
        history.append({"role": "user", "content": message})

        try:
            response = await self._llm.chat(list(history))
        except LLMServiceError:
            history.pop()
            raise

        history.append({"role": "assistant", "content": response})
        return response, sid
