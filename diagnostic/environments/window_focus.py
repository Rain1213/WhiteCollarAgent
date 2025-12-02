"""Diagnostic environment for the "window focus" action."""
from __future__ import annotations

from diagnostic.framework import ActionTestCase


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="window focus",
        base_input={},
        skip_reason=(
            "Interacts with live OS window managers via pyautogui/win32 APIs, which are"
            " unavailable in the diagnostic sandbox."
        ),
    )
