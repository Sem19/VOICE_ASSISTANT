from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_stt_service
from app.main import app
from app.services.stt.base import STTService, TranscriptionResult


@pytest.fixture
def mock_stt() -> MagicMock:
    stt = MagicMock(spec=STTService)
    stt.transcribe.return_value = TranscriptionResult(
        text="recognized speech",
        language="en",
        duration_seconds=4.2,
    )
    return stt


@pytest.fixture
def transcribe_client(mock_stt: MagicMock) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_stt_service] = lambda: mock_stt
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_transcribe_returns_text(transcribe_client: TestClient, mock_stt: MagicMock) -> None:
    response = transcribe_client.post(
        "/transcribe",
        files={"file": ("sample.wav", b"fake-audio-data", "audio/wav")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "text": "recognized speech",
        "language": "en",
        "duration_seconds": 4.2,
    }
    mock_stt.transcribe.assert_called_once()
    assert mock_stt.transcribe.call_args.args[0].endswith(".wav")


def test_transcribe_accepts_mp3_and_m4a(transcribe_client: TestClient, mock_stt: MagicMock) -> None:
    for filename, content_type in (
        ("sample.mp3", "audio/mpeg"),
        ("sample.m4a", "audio/mp4"),
        ("sample.flac", "audio/flac"),
    ):
        response = transcribe_client.post(
            "/transcribe",
            files={"file": (filename, b"fake-audio-data", content_type)},
        )
        assert response.status_code == 200

    assert mock_stt.transcribe.call_count == 3


def test_transcribe_rejects_unsupported_format(transcribe_client: TestClient) -> None:
    response = transcribe_client.post(
        "/transcribe",
        files={"file": ("sample.txt", b"not-audio", "text/plain")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_transcribe_rejects_empty_file(transcribe_client: TestClient) -> None:
    response = transcribe_client.post(
        "/transcribe",
        files={"file": ("sample.wav", b"", "audio/wav")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Empty audio file"


def test_transcribe_returns_500_on_service_error(
    transcribe_client: TestClient,
    mock_stt: MagicMock,
) -> None:
    from app.services.stt.base import STTServiceError

    mock_stt.transcribe.side_effect = STTServiceError("Transcription failed")

    response = transcribe_client.post(
        "/transcribe",
        files={"file": ("sample.wav", b"fake-audio-data", "audio/wav")},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Transcription failed"
