import wave
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_voice_pipeline_service
from app.main import app
from app.services.chat import ChatService
from app.services.llm.base import LLMServiceError
from app.services.stt.base import STTService, STTServiceError, TranscriptionResult
from app.services.tts.base import TTSService, TTSServiceError
from app.services.voice.pipeline import VoicePipelineService


def _make_wav_bytes() -> bytes:
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(b"\x00\x00" * 100)
    return buffer.getvalue()


@pytest.fixture
def mock_stt() -> MagicMock:
    stt = MagicMock(spec=STTService)
    stt.transcribe.return_value = TranscriptionResult(
        text="user recognized text",
        language="en",
        duration_seconds=4.2,
    )
    return stt


@pytest.fixture
def mock_chat() -> AsyncMock:
    chat = AsyncMock(spec=ChatService)
    chat.send_message.return_value = ("assistant answer", "demo-session")
    return chat


@pytest.fixture
def mock_tts(tmp_path: Path) -> MagicMock:
    output_path = tmp_path / "response.wav"
    output_path.write_bytes(_make_wav_bytes())

    tts = MagicMock(spec=TTSService)
    tts.synthesize.return_value = output_path
    return tts


@pytest.fixture
def voice_pipeline(
    mock_stt: MagicMock,
    mock_chat: AsyncMock,
    mock_tts: MagicMock,
) -> VoicePipelineService:
    return VoicePipelineService(
        stt=mock_stt,
        chat=mock_chat,
        tts=mock_tts,
    )


@pytest.fixture
def voice_client(voice_pipeline: VoicePipelineService) -> TestClient:
    app.dependency_overrides[get_voice_pipeline_service] = lambda: voice_pipeline
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_voice_returns_wav_file(voice_client: TestClient) -> None:
    response = voice_client.post(
        "/voice",
        files={"file": ("sample.wav", b"fake-audio-data", "audio/wav")},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content.startswith(b"RIFF")


def test_voice_with_return_debug_returns_json(voice_client: TestClient) -> None:
    response = voice_client.post(
        "/voice",
        files={"file": ("sample.wav", b"fake-audio-data", "audio/wav")},
        data={"session_id": "demo-session", "return_debug": "true"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["transcription"] == "user recognized text"
    assert data["llm_response"] == "assistant answer"
    assert data["audio_file_path"].endswith(".wav")
    assert set(data["latency"]) == {"stt_ms", "llm_ms", "tts_ms", "total_ms"}


def test_voice_rejects_empty_file(voice_client: TestClient) -> None:
    response = voice_client.post(
        "/voice",
        files={"file": ("sample.wav", b"", "audio/wav")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Empty audio file"


def test_voice_returns_500_on_stt_error(
    voice_client: TestClient,
    mock_stt: MagicMock,
) -> None:
    mock_stt.transcribe.side_effect = STTServiceError("STT failed")

    response = voice_client.post(
        "/voice",
        files={"file": ("sample.wav", b"fake-audio-data", "audio/wav")},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "STT failed"


def test_voice_returns_500_on_llm_error(
    voice_client: TestClient,
    mock_chat: AsyncMock,
) -> None:
    mock_chat.send_message.side_effect = LLMServiceError("LLM failed", status_code=500)

    response = voice_client.post(
        "/voice",
        files={"file": ("sample.wav", b"fake-audio-data", "audio/wav")},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "LLM failed"


def test_voice_returns_500_on_tts_error(
    voice_client: TestClient,
    mock_tts: MagicMock,
) -> None:
    mock_tts.synthesize.side_effect = TTSServiceError("TTS failed")

    response = voice_client.post(
        "/voice",
        files={"file": ("sample.wav", b"fake-audio-data", "audio/wav")},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "TTS failed"
