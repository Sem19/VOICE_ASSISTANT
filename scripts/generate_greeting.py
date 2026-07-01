#!/usr/bin/env python3
"""Generate the Asterisk GSM greeting file from VOICE_GREETING."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate_phone_sounds import generate_all_phone_sounds


def main() -> int:
    try:
        outputs = generate_all_phone_sounds()
    except Exception as exc:
        print(f"Failed to generate greeting: {exc}", file=sys.stderr)
        return 1

    for path in outputs:
        print(f"Generated: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
