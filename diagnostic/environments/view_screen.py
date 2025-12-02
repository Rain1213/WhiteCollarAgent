"""Diagnostic environment for the "view screen" action."""
from __future__ import annotations

from diagnostic.framework import ActionTestCase


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="view screen",
        base_input={},
        skip_reason=(
            "Requires InternalActionInterface.describe_screen to capture real desktop state,"
            " which is not available in diagnostics."
        ),
    )
