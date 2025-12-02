"""Diagnostic environment for the "compress files or folders" action."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, Mapping, Tuple

from diagnostic.framework import ActionTestCase, ExecutionResult, PreparedEnv


def prepare_compress(tmp_path: Path, action: Mapping[str, Any]) -> PreparedEnv:  # noqa: ARG001
    data_dir = tmp_path / "data"
    nested_dir = data_dir / "nested"
    data_dir.mkdir()
    nested_dir.mkdir()

    file_one = data_dir / "alpha.txt"
    file_two = nested_dir / "beta.txt"
    file_one.write_text("alpha", encoding="utf-8")
    file_two.write_text("beta", encoding="utf-8")

    archive_path = tmp_path / "archive.zip"

    return PreparedEnv(
        input_overrides={
            "paths": [str(file_one), str(nested_dir)],
            "archive_path": str(archive_path),
        },
        context={
            "expected_archive": str(archive_path),
            "expected_members": {
                str(file_one.resolve()),
                str(nested_dir.resolve()),
            },
            "nested_file": str(file_two),
        },
    )


def validate_compress(
    result: ExecutionResult,
    input_data: Mapping[str, Any],  # noqa: ARG001
    context: Mapping[str, Any],
) -> Tuple[str, str]:
    output = result.parsed_output or {}
    if not isinstance(output, Mapping):
        return "incorrect result", "Expected JSON object output."

    if output.get("status") != "success":
        message = output.get("message", "No message provided")
        return "error", f"Action reported failure: {message}"

    archive_path = context.get("expected_archive")
    if output.get("archive_path") != archive_path:
        return (
            "incorrect result",
            f"Archive path mismatch. expected={archive_path} actual={output.get('archive_path')}",
        )

    compressed_list = {str(Path(p).resolve()) for p in output.get("compressed", [])}
    if compressed_list != context.get("expected_members"):
        return (
            "incorrect result",
            "Compressed entries did not match expectation.",
        )

    archive_file = Path(archive_path)
    if not archive_file.exists():
        return "error", "Archive file was not created."

    with zipfile.ZipFile(archive_file, "r") as zf:
        names = set(zf.namelist())
        if "alpha.txt" not in names or "nested/beta.txt" not in names:
            return (
                "incorrect result",
                f"Archive members incorrect: {json.dumps(sorted(names))}",
            )

        nested_content = zf.read("nested/beta.txt").decode("utf-8")
        if nested_content != "beta":
            return "incorrect result", "Nested file content mismatch."

    return "passed", "Files compressed successfully."


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="compress files or folders",
        base_input={},
        prepare=prepare_compress,
        validator=validate_compress,
    )
