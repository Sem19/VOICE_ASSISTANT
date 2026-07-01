import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

pytest_plugins = ["tests.test_voice"]

from app.api.deps import get_voice_pipeline_service
from app.main import app
from app.services.chat import ChatService
from app.services.stt.base import STTService, TranscriptionResult
from app.services.tts.base import TTSService
from app.services.voice.pipeline import VoicePipelineService
from tests.test_voice import _make_wav_bytes, mock_tts


@pytest.fixture
def multiturn_pipeline(mock_tts: MagicMock) -> VoicePipelineService:
    stt = MagicMock(spec=STTService)
    stt.transcribe.return_value = TranscriptionResult(
        text="first question",
        language="en",
        duration_seconds=2.0,
    )

    chat = AsyncMock(spec=ChatService)
    chat.send_message.side_effect = [
        ("first answer", "session-abc"),
        ("second answer", "session-abc"),
    ]

    return VoicePipelineService(stt=stt, chat=chat, tts=mock_tts)


@pytest.fixture
def multiturn_client(multiturn_pipeline: VoicePipelineService) -> TestClient:
    app.dependency_overrides[get_voice_pipeline_service] = lambda: multiturn_pipeline
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_voice_keeps_session_history_across_turns(
    multiturn_client: TestClient,
    multiturn_pipeline: VoicePipelineService,
) -> None:
    chat = multiturn_pipeline._chat

    first = multiturn_client.post(
        "/voice",
        files={"file": ("sample.wav", _make_wav_bytes(), "audio/wav")},
        data={
            "session_id": "session-abc",
            "call_id": "call-1",
            "turn_number": "1",
        },
    )
    second = multiturn_client.post(
        "/voice",
        files={"file": ("sample.wav", _make_wav_bytes(), "audio/wav")},
        data={
            "session_id": "session-abc",
            "call_id": "call-1",
            "turn_number": "2",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert chat.send_message.await_count == 2
    assert chat.send_message.await_args_list[0].kwargs["session_id"] == "session-abc"
    assert chat.send_message.await_args_list[1].kwargs["session_id"] == "session-abc"


def test_voice_sets_end_call_header_on_goodbye(
    voice_client: TestClient,
    mock_stt: MagicMock,
) -> None:
    mock_stt.transcribe.return_value = TranscriptionResult(
        text="goodbye",
        language="en",
        duration_seconds=1.0,
    )

    response = voice_client.post(
        "/voice",
        files={"file": ("sample.wav", _make_wav_bytes(), "audio/wav")},
        data={
            "session_id": "session-abc",
            "call_id": "call-1",
            "turn_number": "1",
        },
    )

    assert response.status_code == 200
    assert response.headers["X-End-Call"] == "true"
    assert response.headers["X-Call-Id"] == "call-1"
    assert response.headers["X-Turn-Number"] == "1"


def test_voice_sets_end_call_header_on_max_turn(
    voice_client: TestClient,
) -> None:
    response = voice_client.post(
        "/voice",
        files={"file": ("sample.wav", _make_wav_bytes(), "audio/wav")},
        data={
            "session_id": "session-abc",
            "call_id": "call-1",
            "turn_number": "5",
        },
    )

    assert response.status_code == 200
    assert response.headers["X-End-Call"] == "true"
