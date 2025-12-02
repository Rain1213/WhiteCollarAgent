"""Diagnostic environment for the "mark task cancel" action."""
from __future__ import annotations

from diagnostic.framework import ActionTestCase


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="mark task cancel",
        base_input={},
        skip_reason=(
            "Requires InternalActionInterface.mark_task_cancel to communicate with the host system."
        ),
    )
