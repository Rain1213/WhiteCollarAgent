"""Diagnostic environment for the "shell view (windows)" action."""
from __future__ import annotations

from diagnostic.framework import ActionTestCase


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="shell view (windows)",
        base_input={},
        skip_reason="Windows-specific shell inspection not supported in the Linux diagnostic environment.",
    )
