"""Diagnostic environment for the "get current time" action."""
from __future__ import annotations

import types
from typing import Any, Mapping, Tuple

from diagnostic.framework import ActionTestCase, ExecutionResult, PreparedEnv


FIXED_TIMESTAMP = "2025-01-02 03:04:05"


def _build_datetime_stub(timestamp: str) -> types.ModuleType:
    module = types.ModuleType("datetime")

    class _FixedDatetime:
        @classmethod
        def now(cls) -> _FixedDatetime:  # type: ignore[name-defined]
            return cls()

        def strftime(self, _format: str) -> str:  # noqa: D401, ANN001
            return timestamp

    module.datetime = _FixedDatetime
    return module


def prepare_get_current_time(tmp_path, action: Mapping[str, Any]) -> PreparedEnv:  # noqa: ARG001, ANN001
    datetime_stub = _build_datetime_stub(FIXED_TIMESTAMP)
    return PreparedEnv(
        extra_modules={"datetime": datetime_stub},
        context={"expected_time": FIXED_TIMESTAMP},
    )


def validate_get_current_time(
    result: ExecutionResult,
    input_data: Mapping[str, Any],  # noqa: ARG001
    context: Mapping[str, Any],
) -> Tuple[str, str]:
    output = result.parsed_output or {}
    if not isinstance(output, Mapping):
        return "incorrect result", "Expected JSON object output."

    expected_time = context.get("expected_time")
    if output.get("time") != expected_time:
        return (
            "incorrect result",
            f"Timestamp mismatch. expected={expected_time} actual={output.get('time')}",
        )

    return "passed", "Current time returned deterministic timestamp."


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="get current time",
        base_input={},
        prepare=prepare_get_current_time,
        validator=validate_get_current_time,
    )
