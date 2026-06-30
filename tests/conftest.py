from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_chat_service
from app.main import app
from app.services.chat import ChatService
from app.services.llm.base import LLMService


@pytest.fixture
def mock_llm() -> AsyncMock:
    llm = AsyncMock(spec=LLMService)
    llm.chat.return_value = "Hello! How can I help you?"
    return llm


@pytest.fixture
def client(mock_llm: AsyncMock) -> Generator[TestClient, None, None]:
    chat_service = ChatService(llm=mock_llm)
    app.dependency_overrides[get_chat_service] = lambda: chat_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
