#!/usr/bin/env python3
"""Generate custom Asterisk GSM sounds for the voice assistant call flow."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from app.core.config import settings
from app.services.tts.piper import PiperTTSService

SOUNDS_DIR = Path("asterisk/sounds")


def wav_to_gsm(wav_path: Path, gsm_path: Path) -> None:
    gsm_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(wav_path),
            "-ar",
            "8000",
            "-ac",
            "1",
            "-f",
            "gsm",
            str(gsm_path),
        ],
        check=True,
        capture_output=True,
    )


def synthesize_prompt(text: str, gsm_path: Path, tts: PiperTTSService) -> None:
    wav_path = tts.synthesize(text)
    wav_to_gsm(wav_path, gsm_path)
    wav_path.unlink(missing_ok=True)


def generate_tone_beep(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:duration=0.45",
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


def generate_thinking_hold(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1.5",
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


def generate_all_phone_sounds(sounds_dir: Path = SOUNDS_DIR) -> list[Path]:
    sounds_dir.mkdir(parents=True, exist_ok=True)
    tts = PiperTTSService(
        model_path=settings.PIPER_MODEL_PATH,
        config_path=settings.PIPER_CONFIG_PATH,
        output_dir=settings.TTS_OUTPUT_DIR,
    )

    outputs: list[Path] = []

    greeting_path = sounds_dir / "ai-greeting.gsm"
    synthesize_prompt(settings.VOICE_GREETING, greeting_path, tts)
    outputs.append(greeting_path)

    thinking_path = sounds_dir / "thinking.gsm"
    synthesize_prompt(settings.VOICE_THINKING_PROMPT, thinking_path, tts)
    outputs.append(thinking_path)

    beep_path = sounds_dir / "beep.gsm"
    generate_tone_beep(beep_path)
    outputs.append(beep_path)

    hold_path = sounds_dir / "thinking-hold.gsm"
    generate_thinking_hold(hold_path)
    outputs.append(hold_path)

    return outputs


def main() -> int:
    try:
        outputs = generate_all_phone_sounds()
    except Exception as exc:
        print(f"Failed to generate phone sounds: {exc}", file=sys.stderr)
        return 1

    for path in outputs:
        print(f"Generated: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
