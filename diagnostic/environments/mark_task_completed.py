"""Diagnostic environment for the "mark task completed" action."""
from __future__ import annotations

from diagnostic.framework import ActionTestCase


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="mark task completed",
        base_input={},
        skip_reason=(
            "Requires InternalActionInterface.mark_task_completed which is unavailable in tests."
        ),
    )
