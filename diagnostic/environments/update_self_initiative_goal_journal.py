"""Diagnostic environment for the "update self-initiative goal journal" action."""
from __future__ import annotations

import types
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Tuple

from diagnostic.framework import ActionTestCase, ExecutionResult, PreparedEnv


EXPECTED_GOAL_ID = "goal-1234"
EXPECTED_NEW_INFO = "- [action] Added diagnostics"
UPDATED_JOURNAL = (
    "# Status\n- Diagnostics expanded.\n"
    "# Plan\n- Add regression coverage.\n"
    "# History\n- Previous entries consolidated.\n"
    "# Materials\n- /docs/diagnostics.md\n"
    "# Next\n- Monitor action health."
)


def _build_internal_interface_stub(goal_id: str, journal: str) -> types.ModuleType:
    module = types.ModuleType("core.internal_action_interface")

    class InternalActionInterface:  # noqa: D401
        @staticmethod
        async def update_self_initiative_goal_journal(
            *, goal_id: str, new_information: str
        ) -> Mapping[str, Any]:
            if goal_id != EXPECTED_GOAL_ID:
                raise AssertionError(f"Unexpected goal_id {goal_id!r}")
            if new_information != EXPECTED_NEW_INFO:
                raise AssertionError(
                    f"Unexpected new_information {new_information!r}"
                )

            timestamp = datetime(2025, 1, 3, 4, 5, 6).isoformat() + "Z"
            return {
                "status": "ok",
                "goal": {
                    "goal_id": goal_id,
                    "journal": journal,
                    "updated_at": timestamp,
                },
            }

    module.InternalActionInterface = InternalActionInterface
    return module


def _prepare_update_self_initiative_goal_journal(
    tmp_path: Path,  # noqa: ARG001
    action: Mapping[str, Any],  # noqa: ARG001
) -> PreparedEnv:
    internal_stub = _build_internal_interface_stub(
        goal_id=EXPECTED_GOAL_ID,
        journal=UPDATED_JOURNAL,
    )

    return PreparedEnv(
        input_overrides={
            "goal_id": EXPECTED_GOAL_ID,
            "new_information": EXPECTED_NEW_INFO,
        },
        extra_modules={"core.internal_action_interface": internal_stub},
        context={
            "expected_goal_id": EXPECTED_GOAL_ID,
            "expected_journal": UPDATED_JOURNAL,
        },
    )


def _validate_update_self_initiative_goal_journal(
    result: ExecutionResult,
    input_data: Mapping[str, Any],  # noqa: ARG001
    context: Mapping[str, Any],
) -> Tuple[str, str]:
    payload = result.parsed_output
    if not isinstance(payload, Mapping):
        return "incorrect result", "Output must be a JSON object."

    if payload.get("status") != "ok":
        return "error", f"Action reported failure: {payload}"

    goal = payload.get("goal")
    if not isinstance(goal, Mapping):
        return "incorrect result", "'goal' field must be a JSON object."

    if goal.get("goal_id") != context.get("expected_goal_id"):
        return (
            "incorrect result",
            "Returned goal_id does not match expected identifier.",
        )

    if goal.get("journal") != context.get("expected_journal"):
        return "incorrect result", "Journal content does not match stubbed output."

    if "updated_at" not in goal:
        return "incorrect result", "Updated goal must include an 'updated_at' timestamp."

    return "passed", "Self-initiative goal journal updated successfully."


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="update self-initiative goal journal",
        base_input={"goal_id": ""},
        prepare=_prepare_update_self_initiative_goal_journal,
        validator=_validate_update_self_initiative_goal_journal,
    )
