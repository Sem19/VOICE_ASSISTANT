from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_chat_service
from app.main import app
from app.services.chat import ChatService
from app.services.llm.base import LLMServiceUnavailableError
from app.services.llm.ollama import OllamaService


def test_chat_returns_response(client: TestClient) -> None:
    response = client.post("/chat", json={"message": "Hello"})

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Hello! How can I help you?"
    assert "session_id" in data


def test_chat_keeps_session_history(client: TestClient, mock_llm: AsyncMock) -> None:
    first = client.post("/chat", json={"message": "Hello"})
    session_id = first.json()["session_id"]

    client.post("/chat", json={"message": "Follow up", "session_id": session_id})

    assert mock_llm.chat.call_count == 2
    second_call_messages = mock_llm.chat.call_args_list[1].args[0]
    assert len(second_call_messages) == 3
    assert second_call_messages[0]["content"] == "Hello"
    assert second_call_messages[1]["content"] == "Hello! How can I help you?"
    assert second_call_messages[2]["content"] == "Follow up"


def test_chat_returns_503_when_ollama_unavailable(mock_llm: AsyncMock) -> None:
    mock_llm.chat.side_effect = LLMServiceUnavailableError("Ollama service is unavailable")
    chat_service = ChatService(llm=mock_llm)
    app.dependency_overrides[get_chat_service] = lambda: chat_service

    with TestClient(app) as client:
        response = client.post("/chat", json={"message": "Hello"})

    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == "Ollama service is unavailable"


def test_chat_rejects_empty_message(client: TestClient) -> None:
    response = client.post("/chat", json={"message": ""})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ollama_service_returns_assistant_message() -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {"role": "assistant", "content": "Hello! How can I help you?"}
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch(
        "app.services.llm.ollama.httpx.AsyncClient",
        return_value=mock_client,
    ):
        service = OllamaService(
            base_url="http://localhost:11434",
            model="llama3.2",
        )
        result = await service.chat([{"role": "user", "content": "Hello"}])

    assert result == "Hello! How can I help you?"
    mock_client.post.assert_awaited_once_with(
        "http://localhost:11434/api/chat",
        json={
            "model": "llama3.2",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        },
    )


@pytest.mark.asyncio
async def test_ollama_service_raises_when_unavailable() -> None:
    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ConnectError("connection refused")
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch(
        "app.services.llm.ollama.httpx.AsyncClient",
        return_value=mock_client,
    ):
        service = OllamaService(
            base_url="http://localhost:11434",
            model="llama3.2",
        )
        with pytest.raises(LLMServiceUnavailableError):
            await service.chat([{"role": "user", "content": "Hello"}])
