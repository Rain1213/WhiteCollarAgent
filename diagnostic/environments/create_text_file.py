"""Diagnostic environment for the "create text file" action."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Tuple

from diagnostic.framework import ActionTestCase, ExecutionResult, PreparedEnv


FILE_CONTENT = "Diagnostic text file contents."


def prepare_create_text_file(tmp_path: Path, action: Mapping[str, Any]) -> PreparedEnv:  # noqa: ARG001
    file_path = tmp_path / "note.txt"
    return PreparedEnv(
        input_overrides={
            "file_path": str(file_path),
            "file_content": FILE_CONTENT,
        },
        context={
            "file_path": str(file_path),
            "expected_content": FILE_CONTENT,
        },
    )


def validate_create_text_file(
    result: ExecutionResult,
    input_data: Mapping[str, Any],  # noqa: ARG001
    context: Mapping[str, Any],
) -> Tuple[str, str]:
    output = result.parsed_output or {}
    if not isinstance(output, Mapping):
        return "incorrect result", "Expected JSON object output."

    if output.get("status") != "success":
        return "error", f"Action reported failure: {output}"

    expected_path = context.get("file_path")
    if output.get("path") != expected_path:
        return (
            "incorrect result",
            f"Path mismatch. expected={expected_path} actual={output.get('path')}",
        )

    written_path = Path(expected_path)
    if not written_path.exists():
        return "error", "Text file was not created."

    if written_path.read_text(encoding="utf-8") != context.get("expected_content"):
        return "incorrect result", "File content does not match expected text."

    return "passed", "Text file created with expected content."


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="create text file",
        base_input={},
        prepare=prepare_create_text_file,
        validator=validate_create_text_file,
    )
