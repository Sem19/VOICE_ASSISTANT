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
REQUEST_TIMEOUT = float(os.environ.get("VOICE_API_TIMEOUT", "300"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


class VoiceBridgeError(Exception):
    """Raised when the Asterisk-to-voice API bridge fails."""


def flag_path(call_id: str, name: str) -> Path:
    return Path(f"/tmp/voice_{call_id}.{name}")


def clear_turn_flags(call_id: str) -> None:
    for name in ("hangup", "error"):
        flag_path(call_id, name).unlink(missing_ok=True)


def mark_turn_flag(call_id: str, name: str) -> None:
    flag_path(call_id, name).touch(exist_ok=True)


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
    session_id: str,
    call_id: str,
    turn_number: int,
    client: httpx.Client | None = None,
) -> bool:
    """Send one conversation turn to /voice. Returns True when the call should end."""
    if not input_path.is_file():
        raise VoiceBridgeError(f"Input file not found: {input_path}")

    clear_turn_flags(call_id)

    prepared_input = Path(f"/tmp/caller_prepared_{call_id}_{turn_number}.wav")
    api_response = Path(f"/tmp/api_response_{call_id}_{turn_number}.wav")

    owns_client = client is None
    http = client or httpx.Client(timeout=REQUEST_TIMEOUT)

    try:
        logger.info(
            "Voice bridge turn call_id=%s turn=%d session_id=%s input=%s",
            call_id,
            turn_number,
            session_id,
            input_path,
        )
        convert_to_voice_input(input_path, prepared_input)

        logger.info("POST %s", api_url)
        with prepared_input.open("rb") as audio_file:
            response = http.post(
                api_url,
                files={"file": ("caller.wav", audio_file, "audio/wav")},
                data={
                    "session_id": session_id,
                    "call_id": call_id,
                    "turn_number": str(turn_number),
                    "return_debug": "false",
                },
            )
        response.raise_for_status()

        if response.headers.get("content-type", "").split(";")[0] != "audio/wav":
            raise VoiceBridgeError(
                f"Unexpected content type: {response.headers.get('content-type')}"
            )

        end_call = response.headers.get("X-End-Call", "false").lower() == "true"
        logger.info(
            "Voice bridge response call_id=%s turn=%d end_call=%s bytes=%d",
            call_id,
            turn_number,
            end_call,
            len(response.content),
        )

        api_response.write_bytes(response.content)
        output_path.unlink(missing_ok=True)
        convert_for_asterisk(api_response, output_path)
        output_path.chmod(0o666)
        logger.info("Saved Asterisk playback file: %s", output_path)

        if end_call:
            mark_turn_flag(call_id, "hangup")

        return end_call
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode() if exc.stderr else str(exc)
        mark_turn_flag(call_id, "error")
        raise VoiceBridgeError(f"ffmpeg conversion failed: {stderr}") from exc
    except httpx.HTTPStatusError as exc:
        mark_turn_flag(call_id, "error")
        raise VoiceBridgeError(
            f"Voice API error {exc.response.status_code}: {exc.response.text}"
        ) from exc
    except httpx.RequestError as exc:
        mark_turn_flag(call_id, "error")
        raise VoiceBridgeError(f"Voice API request failed: {exc}") from exc
    finally:
        prepared_input.unlink(missing_ok=True)
        api_response.unlink(missing_ok=True)
        if owns_client:
            http.close()


def main() -> int:
    if len(sys.argv) not in (3, 6):
        logger.error(
            "Usage: send_to_voice_api.py <input_wav> <output_gsm> "
            "[session_id call_id turn_number]"
        )
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if len(sys.argv) == 6:
        session_id = sys.argv[3]
        call_id = sys.argv[4]
        turn_number = int(sys.argv[5])
    else:
        session_id = os.environ.get("VOICE_SESSION_ID", "asterisk-call")
        call_id = session_id
        turn_number = 1

    try:
        send_audio_to_voice_api(
            input_path,
            output_path,
            session_id=session_id,
            call_id=call_id,
            turn_number=turn_number,
        )
        return 0
    except VoiceBridgeError as exc:
        logger.error("Voice bridge failed call_id=%s turn=%s: %s", call_id, turn_number, exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
