"""Diagnostic environment for the "replace file str" action."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from diagnostic.framework import ActionTestCase, ExecutionResult, PreparedEnv


def get_test_case() -> ActionTestCase:
    def prepare(tmp_path: Path, action: Mapping[str, Any]) -> PreparedEnv:  # noqa: ARG001
        file_path = tmp_path / "notes" / "summary.txt"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("Alpha beta ALPHA", encoding="utf-8")

        return PreparedEnv(
            input_overrides={
                "file_path": str(file_path),
                "search": "alpha",
                "replace": "omega",
                "ignore_case": True,
            },
            context={"file_path": file_path},
        )

    def validator(
        result: ExecutionResult,
        input_data: Mapping[str, Any],
        context: Mapping[str, Any],
    ) -> tuple[str, str]:
        if result.has_error():
            return "error", "Execution raised an exception."

        payload = result.parsed_output or {}
        if payload.get("status") != "success":
            return "incorrect result", f"Unexpected status: {payload.get('status')!r}."
        if payload.get("replacements") != 2:
            return "incorrect result", "Expected two replacements to occur."
        if payload.get("message") not in ("", None):
            return "incorrect result", "Message should be empty when replacements occur."

        contents = context["file_path"].read_text(encoding="utf-8")
        if contents != "omega beta omega":
            return "incorrect result", f"Unexpected file contents after replacement: {contents!r}."

        return "passed", "File substitutions applied successfully."

    return ActionTestCase(
        name="replace file str",
        base_input={},
        prepare=prepare,
        validator=validator,
    )
