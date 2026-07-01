#!/usr/bin/env python3
"""AGI helper: play thinking audio while /voice is processed."""

from __future__ import annotations

import sys
import threading
from pathlib import Path

from send_to_voice_api import VoiceBridgeError, send_audio_to_voice_api

THINKING_PROMPT = "custom/thinking"
THINKING_HOLD = "custom/thinking-hold"


class AGI:
    def __init__(self) -> None:
        self.env: dict[str, str] = {}
        while True:
            line = sys.stdin.readline()
            if not line.strip():
                break
            key, _, value = line.partition(":")
            self.env[key.strip()] = value.strip()

    def command(self, cmd: str) -> dict[str, str]:
        sys.stdout.write(f"{cmd}\n")
        sys.stdout.flush()

        response: dict[str, str] = {}
        while True:
            line = sys.stdin.readline()
            if not line.strip():
                break
            key, _, value = line.partition(":")
            response[key.strip()] = value.strip()
        return response

    def stream_file(self, filename: str, escape_digits: str = "") -> int:
        response = self.command(f'STREAM FILE {filename} "{escape_digits}"')
        try:
            return int(response.get("result", "-1"))
        except ValueError:
            return -1

    def verbose(self, message: str, level: int = 2) -> None:
        self.command(f'VERBOSE "{message}" {level}')


def play_thinking_loop(agi: AGI, done_event: threading.Event) -> None:
    while not done_event.is_set():
        result = agi.stream_file(THINKING_PROMPT)
        if result < 0:
            return
        if done_event.is_set():
            break
        result = agi.stream_file(THINKING_HOLD)
        if result < 0:
            return


def run_turn(
    input_path: Path,
    output_path: Path,
    session_id: str,
    call_id: str,
    turn_number: int,
) -> int:
    agi = AGI()
    done_event = threading.Event()
    worker_error: list[VoiceBridgeError] = []

    def worker() -> None:
        try:
            send_audio_to_voice_api(
                input_path,
                output_path,
                session_id=session_id,
                call_id=call_id,
                turn_number=turn_number,
            )
        except VoiceBridgeError as exc:
            worker_error.append(exc)
        finally:
            done_event.set()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    play_thinking_loop(agi, done_event)
    thread.join(timeout=300)

    if worker_error:
        agi.verbose(f"Voice turn failed: {worker_error[0]}")
        return 1
    if thread.is_alive():
        agi.verbose("Voice turn timed out")
        return 1
    return 0


def main() -> int:
    if len(sys.argv) != 6:
        print(
            "Usage: voice_turn_agi.py <input_wav> <output_gsm> "
            "<session_id> <call_id> <turn_number>",
            file=sys.stderr,
        )
        return 1

    return run_turn(
        input_path=Path(sys.argv[1]),
        output_path=Path(sys.argv[2]),
        session_id=sys.argv[3],
        call_id=sys.argv[4],
        turn_number=int(sys.argv[5]),
    )


if __name__ == "__main__":
    raise SystemExit(main())
