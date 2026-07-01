import re

GOODBYE_PHRASES = (
    "bye",
    "goodbye",
    "stop",
    "end call",
    "thank you goodbye",
)

_NON_WORD = re.compile(r"[^\w\s]")
_SINGLE_WORD_PHRASES = {"bye", "goodbye", "stop"}


def normalize_utterance(text: str) -> str:
    lowered = text.lower().strip()
    collapsed = _NON_WORD.sub(" ", lowered)
    return " ".join(collapsed.split())


def is_goodbye(text: str) -> bool:
    normalized = normalize_utterance(text)
    if not normalized:
        return False

    words = normalized.split()
    if normalized in _SINGLE_WORD_PHRASES:
        return True
    if words and words[-1] in {"bye", "goodbye"}:
        return True
    if "goodbye" in words:
        return True
    if "stop" in words and len(words) <= 3:
        return True

    for phrase in GOODBYE_PHRASES:
        if " " in phrase and phrase in normalized:
            return True

    return False
