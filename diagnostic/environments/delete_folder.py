"""Diagnostic environment for the "delete folder" action."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Tuple

from diagnostic.framework import ActionTestCase, ExecutionResult, PreparedEnv


def prepare_delete_folder(tmp_path: Path, action: Mapping[str, Any]) -> PreparedEnv:  # noqa: ARG001
    target_dir = tmp_path / "to_remove"
    nested = target_dir / "nested"
    nested.mkdir(parents=True)
    (nested / "marker.txt").write_text("remove me", encoding="utf-8")

    return PreparedEnv(
        input_overrides={"path": str(target_dir)},
        context={"target_path": str(target_dir)},
    )


def validate_delete_folder(
    result: ExecutionResult,
    input_data: Mapping[str, Any],  # noqa: ARG001
    context: Mapping[str, Any],
) -> Tuple[str, str]:
    output = result.parsed_output or {}
    if not isinstance(output, Mapping):
        return "incorrect result", "Expected JSON object output."

    if output.get("status") != "success":
        return "error", f"Action reported failure: {output}"

    target_path = context.get("target_path")
    if output.get("deleted") != target_path:
        return (
            "incorrect result",
            f"Deleted path mismatch. expected={target_path} actual={output.get('deleted')}",
        )

    if Path(target_path).exists():
        return "incorrect result", "Directory still exists after deletion."

    return "passed", "Folder deleted successfully."


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="delete folder",
        base_input={},
        prepare=prepare_delete_folder,
        validator=validate_delete_folder,
    )
