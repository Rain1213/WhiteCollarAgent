"""Diagnostic environment for the "create folder" action."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Tuple

from diagnostic.framework import ActionTestCase, ExecutionResult, PreparedEnv


def prepare_create_folder(tmp_path: Path, action: Mapping[str, Any]) -> PreparedEnv:  # noqa: ARG001
    target_dir = tmp_path / "workspace"

    return PreparedEnv(
        input_overrides={
            "path": str(tmp_path),
            "folder_name": "workspace",
        },
        context={"expected_path": str(target_dir.resolve())},
    )


def validate_create_folder(
    result: ExecutionResult,
    input_data: Mapping[str, Any],
    context: Mapping[str, Any],
) -> Tuple[str, str]:
    output = result.parsed_output or {}
    if not isinstance(output, Mapping):
        return "incorrect result", "Expected JSON object output."

    if output.get("status") != "success":
        message = output.get("message", "No message provided")
        return "error", f"Action reported failure: {message}"

    expected_path = context.get("expected_path")
    if output.get("path") != expected_path:
        return (
            "incorrect result",
            f"Path mismatch. expected={expected_path} actual={output.get('path')}",
        )

    if not Path(expected_path).exists():
        return "error", "Folder was not created on disk."

    return "passed", "Folder created successfully."


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="create folder",
        base_input={},
        prepare=prepare_create_folder,
        validator=validate_create_folder,
    )
