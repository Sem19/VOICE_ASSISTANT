import logging

import httpx

from app.services.llm.base import (
    LLMService,
    LLMServiceError,
    LLMServiceUnavailableError,
)

logger = logging.getLogger(__name__)


class OllamaService(LLMService):
    def __init__(self, base_url: str, model: str, timeout: float = 60.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    async def chat(self, messages: list[dict[str, str]]) -> str:
        url = f"{self._base_url}/api/chat"
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
        except httpx.ConnectError as exc:
            logger.error("Failed to connect to Ollama at %s", self._base_url)
            raise LLMServiceUnavailableError(
                "Ollama service is unavailable"
            ) from exc
        except httpx.TimeoutException as exc:
            logger.error("Ollama request timed out at %s", self._base_url)
            raise LLMServiceUnavailableError(
                "Ollama service timed out"
            ) from exc
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Ollama returned HTTP %s: %s",
                exc.response.status_code,
                exc.response.text,
            )
            raise LLMServiceError(
                f"Ollama request failed: {exc.response.text}",
                status_code=502,
            ) from exc

        data = response.json()
        try:
            return data["message"]["content"]
        except (KeyError, TypeError) as exc:
            logger.error("Unexpected Ollama response format: %s", data)
            raise LLMServiceError(
                "Unexpected response from Ollama",
                status_code=502,
            ) from exc
