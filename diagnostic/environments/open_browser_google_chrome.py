"""Diagnostic environment for the "open browser google chrome" action."""

from __future__ import annotations

import types
from pathlib import Path
from typing import Any, Mapping

from diagnostic.framework import ActionTestCase, ExecutionResult, PreparedEnv


def _build_shutil_stub(chrome_path: Path) -> types.ModuleType:
    module = types.ModuleType("shutil")

    def which(binary: str) -> str | None:
        return str(chrome_path) if binary == "chrome" else None

    module.which = which  # type: ignore[attr-defined]
    return module


def _build_subprocess_stub(invocations: list[list[str]]) -> types.ModuleType:
    module = types.ModuleType("subprocess")
    module.DEVNULL = object()
    module.CREATE_NEW_CONSOLE = 0

    class _Process:
        def __init__(self, cmd: list[str]) -> None:
            self.pid = 31337
            self.cmd = cmd

    def popen(cmd: list[str], *args: Any, **kwargs: Any) -> _Process:  # noqa: ANN401
        invocations.append(list(cmd))
        return _Process(list(cmd))

    module.Popen = popen  # type: ignore[attr-defined]
    return module


def get_test_case() -> ActionTestCase:
    def prepare(tmp_path: Path, action: Mapping[str, Any]) -> PreparedEnv:  # noqa: ARG001
        chrome_path = tmp_path / "chrome" / "chrome.exe"
        chrome_path.parent.mkdir(parents=True)
        chrome_path.write_text("chrome", encoding="utf-8")

        subprocess_calls: list[list[str]] = []

        return PreparedEnv(
            input_overrides={"url": "https://example.test"},
            extra_modules={
                "shutil": _build_shutil_stub(chrome_path),
                "subprocess": _build_subprocess_stub(subprocess_calls),
            },
            context={
                "chrome_path": chrome_path,
                "calls": subprocess_calls,
            },
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
        if payload.get("process_id") != 31337:
            return "incorrect result", "process_id does not match stubbed PID."
        if payload.get("executable_path") != str(context["chrome_path"]):
            return "incorrect result", "Executable path mismatch."
        if payload.get("message") not in ("", None):
            return "incorrect result", "message should be empty on success."

        calls: list[list[str]] = context["calls"]
        if calls != [[str(context["chrome_path"]), "https://example.test"]]:
            return "incorrect result", f"Unexpected launch arguments: {calls!r}."

        return "passed", "Chrome launch simulated."

    return ActionTestCase(
        name="open browser google chrome",
        base_input={},
        prepare=prepare,
        validator=validator,
    )
