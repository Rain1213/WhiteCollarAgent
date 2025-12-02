"""Diagnostic environment for the "update self-initiative goal" action."""
from __future__ import annotations

import types
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Tuple

from diagnostic.framework import ActionTestCase, ExecutionResult, PreparedEnv


EXPECTED_GOAL_ID = "goal-1234"
EXPECTED_TITLE = "Refine agent diagnostics"
EXPECTED_DESCRIPTION = "Expand coverage for action harnesses."
EXPECTED_INTERVAL = "3 days"
EXPECTED_JOURNAL = "# Status\n- Initial setup complete."


def _build_internal_interface_stub(
    expected_op: str,
    expected_title: str,
    expected_description: str,
    expected_interval: str,
    expected_journal: str,
    goal_id: str,
) -> types.ModuleType:
    module = types.ModuleType("core.internal_action_interface")

    class InternalActionInterface:  # noqa: D401
        @staticmethod
        async def upsert_self_initiative_goal(
            *,
            op: str,
            title: str | None,
            description: str | None,
            execution_interval: str | None,
            journal: str | None,
        ) -> Mapping[str, Any]:
            if op != expected_op:
                raise AssertionError(f"Unexpected op {op!r}")
            if title != expected_title:
                raise AssertionError(f"Unexpected title {title!r}")
            if description != expected_description:
                raise AssertionError(f"Unexpected description {description!r}")
            if execution_interval != expected_interval:
                raise AssertionError(f"Unexpected interval {execution_interval!r}")
            if journal != expected_journal:
                raise AssertionError(f"Unexpected journal {journal!r}")

            timestamp = datetime(2025, 1, 2, 3, 4, 5).isoformat() + "Z"
            return {
                "status": "ok",
                "goal": {
                    "goal_id": goal_id,
                    "title": title,
                    "description": description,
                    "execution_interval": execution_interval,
                    "journal": journal,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                    "deleted_at": None,
                },
            }

    module.InternalActionInterface = InternalActionInterface
    return module


def _prepare_update_self_initiative_goal(
    tmp_path: Path,  # noqa: ARG001
    action: Mapping[str, Any],  # noqa: ARG001
) -> PreparedEnv:
    internal_stub = _build_internal_interface_stub(
        expected_op="upsert",
        expected_title=EXPECTED_TITLE,
        expected_description=EXPECTED_DESCRIPTION,
        expected_interval=EXPECTED_INTERVAL,
        expected_journal=EXPECTED_JOURNAL,
        goal_id=EXPECTED_GOAL_ID,
    )

    return PreparedEnv(
        input_overrides={
            "op": "upsert",
            "title": EXPECTED_TITLE,
            "description": EXPECTED_DESCRIPTION,
            "execution_interval": EXPECTED_INTERVAL,
            "journal": EXPECTED_JOURNAL,
        },
        extra_modules={"core.internal_action_interface": internal_stub},
        context={
            "expected_goal_id": EXPECTED_GOAL_ID,
            "expected_title": EXPECTED_TITLE,
            "expected_description": EXPECTED_DESCRIPTION,
            "expected_execution_interval": EXPECTED_INTERVAL,
            "expected_journal": EXPECTED_JOURNAL,
        },
    )


def _validate_update_self_initiative_goal(
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

    for key in ("goal_id", "title", "description", "execution_interval", "journal"):
        expected_value = context.get(f"expected_{key}")
        actual_value = goal.get(key)
        if actual_value != expected_value:
            return (
                "incorrect result",
                f"Goal field {key!r} mismatch: expected {expected_value!r}, got {actual_value!r}.",
            )

    if goal.get("deleted_at") is not None:
        return "incorrect result", "deleted_at should be null for active goals."

    return "passed", "Self-initiative goal updated successfully."


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="update self-initiative goal",
        base_input={"op": "upsert"},
        prepare=_prepare_update_self_initiative_goal,
        validator=_validate_update_self_initiative_goal,
    )
