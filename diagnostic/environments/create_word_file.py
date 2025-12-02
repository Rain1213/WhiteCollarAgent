"""Diagnostic environment for the "create word file" action."""
from __future__ import annotations

import types
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple

from diagnostic.framework import ActionTestCase, ExecutionResult, PreparedEnv


class _Text(str):
    name: None = None  # emulate BeautifulSoup NavigableString interface


class _Tag:
    def __init__(self, name: str, text: str = "", children: Iterable[Any] | None = None) -> None:
        self.name = name
        self._text: _Text | None = _Text(text) if text else None
        self._children: List[Any] = list(children or [])

    def get_text(self, strip: bool = False) -> str:
        parts: List[str] = []
        if self._text:
            parts.append(str(self._text))
        for child in self._children:
            if isinstance(child, _Tag):
                parts.append(child.get_text(strip=strip))
            else:
                parts.append(str(child))
        text = "".join(parts)
        return text.strip() if strip else text

    def find_all(self, name: str) -> List["_Tag"]:
        matches: List[_Tag] = []
        for child in self._children:
            if isinstance(child, _Tag):
                if child.name == name:
                    matches.append(child)
                matches.extend(child.find_all(name))
        return matches

    @property
    def descendants(self) -> Iterable[Any]:
        for child in self._children:
            if isinstance(child, _Tag):
                yield child
                yield from child.descendants
            else:
                yield child
        if self._text:
            yield self._text


def _build_bs4_module() -> types.ModuleType:
    bs4_mod = types.ModuleType("bs4")

    class BeautifulSoup:
        def __init__(self, data: str, parser: str = "html.parser") -> None:  # noqa: ARG002
            self._elements: List[_Tag] = []
            for line in data.splitlines():
                line = line.strip()
                if not line:
                    continue
                if "::" not in line:
                    continue
                prefix, payload = line.split("::", 1)
                prefix = prefix.lower()
                if prefix.startswith("h") and prefix[1:].isdigit():
                    self._elements.append(_Tag(f"h{prefix[1:]}", payload))
                elif prefix == "p":
                    self._elements.append(_Tag("p", payload))

        def _iter_descendants(self) -> Iterable[Any]:
            for element in self._elements:
                yield element
                yield from element.descendants

        @property
        def descendants(self) -> Iterable[Any]:
            return self._iter_descendants()

    bs4_mod.BeautifulSoup = BeautifulSoup  # type: ignore[attr-defined]
    return bs4_mod


def _build_beautifulsoup4_module(bs4_mod: types.ModuleType) -> types.ModuleType:
    beautifulsoup_pkg = types.ModuleType("beautifulsoup4")
    beautifulsoup_pkg.BeautifulSoup = getattr(bs4_mod, "BeautifulSoup")  # type: ignore[attr-defined]
    return beautifulsoup_pkg


def _build_markdown2_module() -> types.ModuleType:
    markdown2_mod = types.ModuleType("markdown2")

    def markdown(text: str) -> str:
        lines = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("# "):
                lines.append(f"H1::{line[2:].strip()}")
            else:
                lines.append(f"P::{line}")
        return "\n".join(lines)

    markdown2_mod.markdown = markdown  # type: ignore[attr-defined]
    return markdown2_mod


def _build_docx_modules(output_marker: str) -> Dict[str, types.ModuleType]:
    docx_pkg = types.ModuleType("docx")
    docx_pkg.__path__ = []  # type: ignore[attr-defined]

    class Document:
        class Run:
            def __init__(self, text: str) -> None:
                self.text = text
                self.bold = False
                self.italic = False

        class Paragraph:
            def __init__(self, style: str | None = None) -> None:
                self.style = style
                self.runs: List[Document.Run] = []

            def add_run(self, text: str) -> "Document.Run":
                run = Document.Run(text)
                self.runs.append(run)
                return run

        def __init__(self) -> None:
            self._entries: List[Tuple[str, Any]] = []

        def add_heading(self, text: str, level: int = 1) -> None:
            self._entries.append(("heading", level, text))

        def add_paragraph(self, text: str = "", style: str | None = None) -> "Document.Paragraph":
            para = Document.Paragraph(style)
            if text:
                para.runs.append(Document.Run(text))
            self._entries.append(("paragraph", para))
            return para

        def save(self, file_path: str) -> None:
            lines: List[str] = []
            for entry in self._entries:
                kind = entry[0]
                if kind == "heading":
                    _, level, text = entry
                    lines.append(f"H{level}:{text}")
                else:
                    _, para = entry
                    text = "".join(run.text for run in para.runs)
                    style = f"[{para.style}]" if para.style else ""
                    lines.append(f"P{style}:{text}")
            Path(file_path).write_text(output_marker + "\n" + "\n".join(lines), encoding="utf-8")

    docx_pkg.Document = Document  # type: ignore[attr-defined]

    shared_mod = types.ModuleType("docx.shared")

    def Pt(size: int) -> int:  # noqa: D401 - simple identity helper
        return size

    shared_mod.Pt = Pt  # type: ignore[attr-defined]

    python_docx_pkg = types.ModuleType("python-docx")

    return {
        "docx": docx_pkg,
        "docx.shared": shared_mod,
        "python-docx": python_docx_pkg,
    }


def prepare_create_word(tmp_path: Path, action: Mapping[str, Any]) -> PreparedEnv:  # noqa: ARG001
    file_path = tmp_path / "document.docx"
    content = "# Diagnostic Heading\nThis is a diagnostic paragraph."
    modules: Dict[str, types.ModuleType] = {}
    modules["markdown2"] = _build_markdown2_module()
    bs4_mod = _build_bs4_module()
    modules["bs4"] = bs4_mod
    modules["beautifulsoup4"] = _build_beautifulsoup4_module(bs4_mod)
    modules.update(_build_docx_modules("DOCX-STUB"))

    return PreparedEnv(
        input_overrides={
            "file_path": str(file_path),
            "content": content,
        },
        extra_modules=modules,
        context={
            "file_path": str(file_path),
            "marker": "DOCX-STUB",
            "heading": "Diagnostic Heading",
            "paragraph": "This is a diagnostic paragraph.",
        },
    )


def validate_create_word(
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

    expected_path = context.get("file_path")
    if output.get("path") != expected_path:
        return (
            "incorrect result",
            f"Path mismatch. expected={expected_path} actual={output.get('path')}",
        )

    doc_path = Path(expected_path)
    if not doc_path.exists():
        return "error", "Word document was not created."

    contents = doc_path.read_text(encoding="utf-8")
    if context.get("marker") not in contents:
        return "incorrect result", "Stub Word marker missing from document."

    if context.get("heading") not in contents or context.get("paragraph") not in contents:
        return "incorrect result", "Document contents missing expected text."

    return "passed", "Word file created with stub backend."


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="create word file",
        base_input={},
        prepare=prepare_create_word,
        validator=validate_create_word,
    )
