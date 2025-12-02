"""Diagnostic environment for the "add number" action."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Tuple

from diagnostic.framework import ActionTestCase, ExecutionResult, PreparedEnv


def _prepare_add_number(tmp_path: Path, action: Mapping[str, Any]) -> PreparedEnv:  # noqa: ARG001
    a_value = 7
    b_value = 5
    return PreparedEnv(
        input_overrides={"a": a_value, "b": b_value},
        context={"expected_sum": a_value + b_value},
    )


def _validate_add_number(
    result: ExecutionResult,
    input_data: Mapping[str, Any],  # noqa: ARG001
    context: Mapping[str, Any],
) -> Tuple[str, str]:
    payload = result.parsed_output
    if not isinstance(payload, Mapping):
        return "incorrect result", "Output must be a JSON object."

    if "result" not in payload:
        return "incorrect result", "Missing 'result' key in output."

    expected_sum = context.get("expected_sum")
    if payload.get("result") != expected_sum:
        return (
            "incorrect result",
            f"Computed sum {payload.get('result')} does not match expected {expected_sum}.",
        )

    return "passed", "Numbers were added correctly."


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="add number",
        base_input={"a": 0, "b": 0},
        prepare=_prepare_add_number,
        validator=_validate_add_number,
    )
