"""Diagnostic environment for the "shell kill process (windows)" action."""
from __future__ import annotations

from diagnostic.framework import ActionTestCase


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="shell kill process (windows)",
        base_input={},
        skip_reason="Windows-specific process management is unavailable in the Linux diagnostic sandbox.",
    )
