"""Diagnostic environment for the "read word file" action."""

from __future__ import annotations

import types
from pathlib import Path
from typing import Any, Mapping

from diagnostic.framework import ActionTestCase, ExecutionResult, PreparedEnv


def _build_python_docx_stubs(document_path: Path) -> dict[str, types.ModuleType]:
    docx_module = types.ModuleType("docx")
    python_docx_pkg = types.ModuleType("python-docx")

    class _Paragraph:
        def __init__(self, text: str) -> None:
            self.text = text

    class Document:
        def __init__(self, file_path: str) -> None:
            if Path(file_path) != document_path:
                raise FileNotFoundError(file_path)
            contents = document_path.read_text(encoding="utf-8").splitlines()
            self.paragraphs = [_Paragraph(text=line) for line in contents]

    docx_module.Document = Document  # type: ignore[attr-defined]

    return {"docx": docx_module, "python-docx": python_docx_pkg}


def get_test_case() -> ActionTestCase:
    def prepare(tmp_path: Path, action: Mapping[str, Any]) -> PreparedEnv:  # noqa: ARG001
        doc_path = tmp_path / "docs" / "report.docx"
        doc_path.parent.mkdir(parents=True)
        doc_path.write_text("Quarterly Results\nRevenue increased", encoding="utf-8")

        extra_modules = _build_python_docx_stubs(doc_path)

        return PreparedEnv(
            input_overrides={"file_path": str(doc_path)},
            extra_modules=extra_modules,
            context={"doc_path": doc_path},
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
        expected = "Quarterly Results Revenue increased"
        if payload.get("content") != expected:
            return "incorrect result", f"Content mismatch: {payload.get('content')!r}."
        if payload.get("message") not in ("", None):
            return "incorrect result", "Message should be omitted on success."

        return "passed", "Word file contents extracted successfully."

    return ActionTestCase(
        name="read word file",
        base_input={"file_path": ""},
        prepare=prepare,
        validator=validator,
    )
