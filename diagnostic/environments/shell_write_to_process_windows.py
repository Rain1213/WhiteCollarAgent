"""Diagnostic environment for the "shell write to process (windows)" action."""
from __future__ import annotations

from diagnostic.framework import ActionTestCase


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="shell write to process (windows)",
        base_input={},
        skip_reason=(
            "Windows-only shell process manipulation is unavailable in the Linux diagnostic sandbox."
        ),
    )
