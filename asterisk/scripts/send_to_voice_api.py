#!/usr/bin/env python3
"""Send recorded caller audio to FastAPI /voice and save the spoken AI response."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

import httpx

DEFAULT_VOICE_API_URL = os.environ.get(
    "VOICE_API_URL",
    "http://voice-ai-backend:8000/voice",
)
DEFAULT_SESSION_ID = os.environ.get("VOICE_SESSION_ID", "asterisk-call")
REQUEST_TIMEOUT = float(os.environ.get("VOICE_API_TIMEOUT", "300"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


class VoiceBridgeError(Exception):
    """Raised when the Asterisk-to-voice API bridge fails."""


def convert_to_voice_input(input_path: Path, output_path: Path) -> None:
    """Convert caller audio to 16 kHz mono WAV for /voice."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-ar",
            "16000",
            "-ac",
            "1",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )


def convert_for_asterisk(input_path: Path, output_path: Path) -> None:
    """Convert API WAV to 8 kHz mono GSM for Asterisk Playback."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-ar",
            "8000",
            "-ac",
            "1",
            "-f",
            "gsm",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )


def send_audio_to_voice_api(
    input_path: Path,
    output_path: Path,
    *,
    api_url: str = DEFAULT_VOICE_API_URL,
    session_id: str = DEFAULT_SESSION_ID,
    client: httpx.Client | None = None,
) -> None:
    if not input_path.is_file():
        raise VoiceBridgeError(f"Input file not found: {input_path}")

    prepared_input = Path("/tmp/caller_prepared.wav")
    api_response = Path("/tmp/api_response.wav")

    owns_client = client is None
    http = client or httpx.Client(timeout=REQUEST_TIMEOUT)

    try:
        logger.info("Converting input for /voice: %s", input_path)
        convert_to_voice_input(input_path, prepared_input)

        logger.info("POST %s", api_url)
        with prepared_input.open("rb") as audio_file:
            response = http.post(
                api_url,
                files={"file": ("caller.wav", audio_file, "audio/wav")},
                data={"session_id": session_id, "return_debug": "false"},
            )
        response.raise_for_status()

        if response.headers.get("content-type", "").split(";")[0] != "audio/wav":
            raise VoiceBridgeError(
                f"Unexpected content type: {response.headers.get('content-type')}"
            )

        api_response.write_bytes(response.content)
        logger.info("Received %d bytes from /voice", len(response.content))

        output_path.unlink(missing_ok=True)
        convert_for_asterisk(api_response, output_path)
        output_path.chmod(0o666)
        logger.info("Saved Asterisk playback file: %s", output_path)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode() if exc.stderr else str(exc)
        raise VoiceBridgeError(f"ffmpeg conversion failed: {stderr}") from exc
    except httpx.HTTPStatusError as exc:
        raise VoiceBridgeError(
            f"Voice API error {exc.response.status_code}: {exc.response.text}"
        ) from exc
    except httpx.RequestError as exc:
        raise VoiceBridgeError(f"Voice API request failed: {exc}") from exc
    finally:
        prepared_input.unlink(missing_ok=True)
        api_response.unlink(missing_ok=True)
        if owns_client:
            http.close()


def main() -> int:
    if len(sys.argv) != 3:
        logger.error("Usage: send_to_voice_api.py <input_wav> <output_wav>")
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    try:
        send_audio_to_voice_api(input_path, output_path)
        return 0
    except VoiceBridgeError as exc:
        logger.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
