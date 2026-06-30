import wave
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_tts_service
from app.main import app
from app.services.tts.base import TTSModelNotFoundError, TTSService, TTSServiceError


def _make_wav_bytes() -> bytes:
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(b"\x00\x00" * 100)
    return buffer.getvalue()


@pytest.fixture
def mock_tts(tmp_path: Path) -> MagicMock:
    output_path = tmp_path / "speech.wav"
    output_path.write_bytes(_make_wav_bytes())

    tts = MagicMock(spec=TTSService)
    tts.synthesize.return_value = output_path
    return tts


@pytest.fixture
def tts_client(mock_tts: MagicMock) -> TestClient:
    app.dependency_overrides[get_tts_service] = lambda: mock_tts
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_tts_returns_wav_file(tts_client: TestClient, mock_tts: MagicMock) -> None:
    response = tts_client.post(
        "/tts",
        json={"text": "Hello, how can I help you?"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content.startswith(b"RIFF")
    mock_tts.synthesize.assert_called_once_with("Hello, how can I help you?")


def test_tts_rejects_empty_text(tts_client: TestClient) -> None:
    response = tts_client.post("/tts", json={"text": ""})

    assert response.status_code == 422


def test_tts_returns_503_when_model_missing(mock_tts: MagicMock) -> None:
    mock_tts.synthesize.side_effect = TTSModelNotFoundError(
        "models/piper/en_US-lessac-medium.onnx"
    )
    app.dependency_overrides[get_tts_service] = lambda: mock_tts

    with TestClient(app) as client:
        response = client.post("/tts", json={"text": "Hello"})

    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert "TTS model not found" in response.json()["detail"]


def test_tts_returns_500_on_service_error(mock_tts: MagicMock) -> None:
    mock_tts.synthesize.side_effect = TTSServiceError("Speech synthesis failed")

    app.dependency_overrides[get_tts_service] = lambda: mock_tts

    with TestClient(app) as client:
        response = client.post("/tts", json={"text": "Hello"})

    app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == "Speech synthesis failed"
