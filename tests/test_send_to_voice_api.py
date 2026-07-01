import sys
import wave
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from send_to_voice_api import VoiceBridgeError, send_audio_to_voice_api


def _make_wav_bytes() -> bytes:
    buffer = BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(8000)
        wav_file.writeframes(b"\x00\x00" * 100)
    return buffer.getvalue()


def test_send_to_voice_api_saves_response_wav(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_path = tmp_path / "caller.wav"
    output_path = tmp_path / "ai_response.wav"
    input_path.write_bytes(_make_wav_bytes())

    response_wav = _make_wav_bytes()

    def fake_convert_to_voice_input(source: Path, destination: Path) -> None:
        destination.write_bytes(source.read_bytes())

    def fake_convert_for_asterisk(source: Path, destination: Path) -> None:
        destination.write_bytes(source.read_bytes())

    mock_response = MagicMock()
    mock_response.headers = {"content-type": "audio/wav"}
    mock_response.content = response_wav
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = mock_response

    monkeypatch.setattr(
        "send_to_voice_api.convert_to_voice_input",
        fake_convert_to_voice_input,
    )
    monkeypatch.setattr(
        "send_to_voice_api.convert_for_asterisk",
        fake_convert_for_asterisk,
    )

    send_audio_to_voice_api(
        input_path,
        output_path,
        client=mock_client,
        api_url="http://voice-ai-backend:8000/voice",
    )

    assert output_path.exists()
    assert output_path.read_bytes() == response_wav
    mock_client.post.assert_called_once()


def test_send_to_voice_api_raises_on_backend_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_path = tmp_path / "caller.wav"
    output_path = tmp_path / "ai_response.wav"
    input_path.write_bytes(_make_wav_bytes())

    monkeypatch.setattr(
        "send_to_voice_api.convert_to_voice_input",
        lambda source, destination: destination.write_bytes(source.read_bytes()),
    )

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = httpx.Response(
        status_code=503,
        text="Ollama service is unavailable",
        request=httpx.Request("POST", "http://voice-ai-backend:8000/voice"),
    )

    with pytest.raises(VoiceBridgeError, match="Voice API error 503"):
        send_audio_to_voice_api(
            input_path,
            output_path,
            client=mock_client,
        )


def test_main_exits_non_zero_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from send_to_voice_api import main

    missing_input = tmp_path / "missing.wav"
    output_path = tmp_path / "ai_response.wav"

    monkeypatch.setattr(
        "sys.argv",
        ["send_to_voice_api.py", str(missing_input), str(output_path)],
    )

    assert main() == 1
