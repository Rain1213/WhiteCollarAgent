"""Diagnostic environment for the "set file public access" action."""

from __future__ import annotations

import types
from pathlib import Path
from typing import Any, Mapping

from diagnostic.framework import ActionTestCase, ExecutionResult, PreparedEnv


def _build_platform_stub() -> types.ModuleType:
    module = types.ModuleType("platform")

    def system() -> str:
        return "Windows"

    module.system = system  # type: ignore[attr-defined]
    return module


def _build_subprocess_stub(commands: list[list[str]], acl_output: str) -> types.ModuleType:
    module = types.ModuleType("subprocess")

    class _Completed:
        def __init__(self, stdout: str, returncode: int = 0) -> None:
            self.stdout = stdout
            self.returncode = returncode

    def run(cmd: list[str], *args: Any, **kwargs: Any) -> _Completed:  # noqa: ANN401
        commands.append(list(cmd))
        if cmd[:2] == ["icacls", acl_output.split(" ", 1)[0]]:
            return _Completed(stdout=acl_output)
        if "icacls" in cmd:
            return _Completed(stdout="processed 1 files")
        raise RuntimeError(f"Unexpected command: {cmd}")

    module.run = run  # type: ignore[attr-defined]
    module.PIPE = object()
    module.STDOUT = object()
    return module


def get_test_case() -> ActionTestCase:
    def prepare(tmp_path: Path, action: Mapping[str, Any]) -> PreparedEnv:  # noqa: ARG001
        target = tmp_path / "shared" / "report.txt"
        target.parent.mkdir(parents=True)
        target.write_text("confidential", encoding="utf-8")

        commands: list[list[str]] = []
        acl_line = f"{target} BUILTIN\\Users:(R)"

        extra_modules = {
            "platform": _build_platform_stub(),
            "subprocess": _build_subprocess_stub(commands, acl_line),
        }

        return PreparedEnv(
            input_overrides={
                "path": str(target),
                "action": "grant",
                "permission": "read",
                "recursive": False,
            },
            extra_modules=extra_modules,
            context={
                "target": target,
                "acl": acl_line,
                "commands": commands,
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
        if payload.get("acl") != context["acl"]:
            return "incorrect result", "Returned ACL did not match stub output."
        if payload.get("message") != "Permission granted.":
            return "incorrect result", "Message did not reflect grant operation."

        commands: list[list[str]] = context["commands"]
        if len(commands) != 2:
            return "incorrect result", f"Expected two icacls commands, saw {len(commands)}."
        grant_cmd, query_cmd = commands
        expected_grant = ["icacls", str(context["target"]), "/grant", "*S-1-1-0:(R)"]
        if grant_cmd != expected_grant:
            return "incorrect result", f"Grant command mismatch: {grant_cmd!r}."
        if query_cmd[:2] != ["icacls", str(context["target"])]:
            return "incorrect result", "ACL query command malformed."

        return "passed", "ACL modification simulated successfully."

    return ActionTestCase(
        name="set file public access",
        base_input={},
        prepare=prepare,
        validator=validator,
    )
