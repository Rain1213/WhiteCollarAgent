"""Diagnostic environment for the "extract ZIP file" action."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Tuple
from zipfile import ZIP_DEFLATED, ZipFile

from diagnostic.framework import ActionTestCase, ExecutionResult, PreparedEnv


def prepare_extract_zip_file(tmp_path: Path, action: Mapping[str, Any]) -> PreparedEnv:  # noqa: ARG001
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "docs").mkdir()

    files = {
        source_dir / "README.txt": "Top-level readme contents.\n",
        source_dir / "docs" / "manual.md": "# Manual\nDetails inside.\n",
    }
    for path, text in files.items():
        path.write_text(text, encoding="utf-8")

    zip_path = tmp_path / "archive.zip"
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, arcname=path.relative_to(source_dir))

    dest_dir = tmp_path / "extracted"

    expected_files = {
        str((dest_dir / path.relative_to(source_dir)).resolve()): content
        for path, content in files.items()
    }

    return PreparedEnv(
        input_overrides={
            "zip_path": str(zip_path),
            "dest_path": str(dest_dir),
        },
        context={
            "dest_path": str(dest_dir.resolve()),
            "expected_files": expected_files,
        },
    )


def validate_extract_zip_file(
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

    expected_dest = context.get("dest_path")
    if output.get("dest_path") != expected_dest:
        return (
            "incorrect result",
            f"Destination mismatch. expected={expected_dest} actual={output.get('dest_path')}",
        )

    extracted = output.get("extracted")
    if not isinstance(extracted, list):
        return "incorrect result", "Expected 'extracted' to be a list of paths."

    expected_files: Mapping[str, str] = context.get("expected_files", {})
    if sorted(extracted) != sorted(expected_files):
        return "incorrect result", json.dumps(
            {
                "expected": sorted(expected_files),
                "actual": sorted(extracted),
            }
        )

    for path_str, expected_contents in expected_files.items():
        path = Path(path_str)
        if not path.exists():
            return "error", f"Extracted file missing on disk: {path_str}"
        if path.read_text(encoding="utf-8") != expected_contents:
            return "incorrect result", f"Content mismatch for {path_str}"

    return "passed", "ZIP archive extracted with expected files."


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="extract ZIP file",
        base_input={},
        prepare=prepare_extract_zip_file,
        validator=validate_extract_zip_file,
    )
