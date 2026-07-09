"""Style reference for future generated pytest files.

This file is a source example for ChatGPT prompts. The repository is currently
checklist-first, so this file documents the desired shape for future generated
tests rather than acting as a collected test module.
"""

import pytest


def test_builtin_dispatches_to_dunder_method():
    class Distance:
        def __init__(self, meters):
            self.meters = meters

        def __abs__(self):
            return abs(self.meters)

    assert abs(Distance(-12)) == 12


def test_index_protocol_is_not_the_same_as_int_protocol():
    class Port:
        def __index__(self):
            return 8080

        def __int__(self):
            return 1

    assert bin(Port()) == bin(8080)
    assert hex(Port()) == hex(8080)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("api/v1", "api-v1"),
        ("user/profile", "user-profile"),
    ],
)
def test_parametrize_small_api_examples(text, expected):
    assert text.replace("/", "-") == expected


def test_documented_exception_shape():
    with pytest.raises(ValueError):
        int("not-a-number")
