"""Diagnostic scenario for the "ask question" action."""
from __future__ import annotations

from diagnostic.framework import ActionTestCase


def get_test_case() -> ActionTestCase:
    """Return a skipped test case because the action depends on runtime services."""
    return ActionTestCase(
        name="ask question",
        skip_reason=(
            "Requires core.internal_action_interface runtime services (state manager, task context) "
            "which are unavailable in the diagnostic sandbox."
        ),
    )
