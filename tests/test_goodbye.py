import pytest

from app.services.voice.goodbye import is_goodbye


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("bye", True),
        ("Goodbye!", True),
        ("thank you goodbye", True),
        ("Thank you, goodbye", True),
        ("end call", True),
        ("please stop", True),
        ("stop", True),
        ("what time is it", False),
        ("maybe later", False),
        ("", False),
    ],
)
def test_is_goodbye(text: str, expected: bool) -> None:
    assert is_goodbye(text) is expected
