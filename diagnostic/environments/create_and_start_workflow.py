"""Diagnostic scenario for the "create and start workflow" action."""
from __future__ import annotations

from diagnostic.framework import ActionTestCase


def get_test_case() -> ActionTestCase:
    """Return a skipped test case because the workflow API is not available."""
    return ActionTestCase(
        name="create and start workflow",
        skip_reason=(
            "Depends on core.internal_action_interface workflow orchestration which requires the full backend "
            "stack and cannot be simulated reliably here."
        ),
    )
