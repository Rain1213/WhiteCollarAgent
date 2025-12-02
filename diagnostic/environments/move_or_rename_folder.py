"""Diagnostic environment for the "move or rename folder" action."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from diagnostic.framework import ActionTestCase, ExecutionResult, PreparedEnv


def _validate_paths(src: Path, dst: Path) -> tuple[bool, str]:
    if src.exists():
        return False, f"Source directory still exists at {src!s}."
    if not dst.exists():
        return False, f"Target directory missing at {dst!s}."
    files = sorted(p.name for p in dst.iterdir())
    if files != ["notes.txt"]:
        return False, f"Unexpected contents in moved directory: {files!r}."
    content = (dst / "notes.txt").read_text(encoding="utf-8")
    if content != "draft":
        return False, "File contents did not survive move operation."
    return True, ""


def get_test_case() -> ActionTestCase:
    def prepare(tmp_path: Path, action: Mapping[str, Any]) -> PreparedEnv:  # noqa: ARG001
        src = tmp_path / "workspace" / "alpha"
        src.mkdir(parents=True)
        (src / "notes.txt").write_text("draft", encoding="utf-8")

        target = tmp_path / "workspace" / "archive" / "alpha_2024"

        context = {
            "source": src,
            "target": target,
        }

        return PreparedEnv(
            input_overrides={
                "source": str(src),
                "target": str(target),
            },
            context=context,
        )

    def validator(
        result: ExecutionResult,
        input_data: Mapping[str, Any],
        context: Mapping[str, Any],
    ) -> tuple[str, str]:
        if result.has_error():
            return "error", "Execution raised an exception."

        payload = result.parsed_output or {}
        expected_source = str(context["source"])
        expected_target = str(context["target"])

        if payload.get("status") != "success":
            return "incorrect result", f"Unexpected status: {payload.get('status')!r}."
        if payload.get("old_path") != expected_source:
            return "incorrect result", "old_path does not match prepared directory."
        if payload.get("new_path") != expected_target:
            return "incorrect result", "new_path does not match expected target."

        ok, message = _validate_paths(Path(expected_source), Path(expected_target))
        if not ok:
            return "incorrect result", message

        return "passed", "Folder moved successfully."

    return ActionTestCase(
        name="move or rename folder",
        base_input={},
        prepare=prepare,
        validator=validator,
    )
