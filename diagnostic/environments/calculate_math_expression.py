"""Diagnostic environment for the "calculate math expression" action."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Tuple

from diagnostic.framework import ActionTestCase, ExecutionResult, PreparedEnv


EXPRESSION = """
result = sum(i * i for i in range(1, 6))
print("calculation complete")
""".strip()

EXPECTED_RESULT = sum(i * i for i in range(1, 6))


def prepare_calculate_math_expression(
    tmp_path: Path,
    action: Mapping[str, Any],  # noqa: ARG001
) -> PreparedEnv:
    return PreparedEnv(
        input_overrides={
            "expression": EXPRESSION,
            "variables": {},
        }
    )


def validate_calculate_math_expression(
    result: ExecutionResult,
    input_data: Mapping[str, Any],  # noqa: ARG001
    context: Mapping[str, Any],  # noqa: ARG001
) -> Tuple[str, str]:
    output = result.parsed_output or {}
    if not isinstance(output, Mapping):
        return "incorrect result", "Expected JSON object output."

    if output.get("status") != "success":
        message = output.get("message", "No message provided")
        return "error", f"Action reported failure: {message}"

    if output.get("result") != EXPECTED_RESULT:
        return (
            "incorrect result",
            f"Unexpected calculation result. expected={EXPECTED_RESULT} actual={output.get('result')}",
        )

    if output.get("stdout") != "calculation complete":
        return (
            "incorrect result",
            f"Unexpected stdout captured: {output.get('stdout')!r}",
        )

    return "passed", "Expression evaluated correctly."


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="calculate math expression",
        base_input={},
        prepare=prepare_calculate_math_expression,
        validator=validate_calculate_math_expression,
    )
