"""Diagnostic environment for the "mark task error" action."""

from __future__ import annotations

from diagnostic.framework import ActionTestCase


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="mark task error",
        base_input={},
        skip_reason=(
            "Requires InternalActionInterface.mark_task_error to communicate with the host system."
        ),
    )
