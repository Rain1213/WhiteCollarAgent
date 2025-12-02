"""Diagnostic environment for the "download message attachment" action."""
from __future__ import annotations

import types
from pathlib import Path
from typing import Any, Mapping, Tuple

from diagnostic.framework import ActionTestCase, ExecutionResult, PreparedEnv


ATTACHMENT_URL = "https://chat.example.com/attachments/abc123"
ATTACHMENT_FILENAME = "report.pdf"
ATTACHMENT_BYTES = b"diagnostic attachment contents"


def _build_internal_interface_stub(
    expected_url: str,
    expected_dest: Path,
    expected_filename: str,
    payload: bytes,
) -> types.ModuleType:
    module = types.ModuleType("core.internal_action_interface")

    class InternalActionInterface:  # noqa: D401 - mimic real interface
        @staticmethod
        async def download_attachment(
            url: str,
            dest_dir: str | None = None,
            filename: str | None = None,
        ) -> str:
            if url != expected_url:
                raise AssertionError(
                    f"Unexpected URL {url!r}; expected {expected_url!r}"
                )

            destination = Path(dest_dir) if dest_dir else expected_dest
            destination.mkdir(parents=True, exist_ok=True)

            chosen_name = filename or expected_filename
            if chosen_name != expected_filename:
                raise AssertionError(
                    f"Unexpected filename {chosen_name!r}; expected {expected_filename!r}"
                )

            target_path = destination / chosen_name
            target_path.write_bytes(payload)
            return str(target_path)

    module.InternalActionInterface = InternalActionInterface
    return module


def _prepare_download_message_attachment(
    tmp_path: Path,
    action: Mapping[str, Any],  # noqa: ARG001
) -> PreparedEnv:
    if isinstance(action, dict) and isinstance(action.get("code"), str):
        # Some deployments store this action's code with literal ``\n`` sequences.
        # Decode them so the script executes as intended during diagnostics.
        action["code"] = action["code"].encode("utf-8").decode("unicode_escape")

    dest_dir = tmp_path / "attachments"
    expected_path = dest_dir / ATTACHMENT_FILENAME

    internal_stub = _build_internal_interface_stub(
        expected_url=ATTACHMENT_URL,
        expected_dest=dest_dir,
        expected_filename=ATTACHMENT_FILENAME,
        payload=ATTACHMENT_BYTES,
    )

    return PreparedEnv(
        input_overrides={
            "url": ATTACHMENT_URL,
            "dest_dir": str(dest_dir),
            "filename": ATTACHMENT_FILENAME,
        },
        extra_modules={"core.internal_action_interface": internal_stub},
        context={
            "expected_path": str(expected_path),
            "expected_bytes": ATTACHMENT_BYTES,
        },
    )


def _validate_download_message_attachment(
    result: ExecutionResult,
    input_data: Mapping[str, Any],  # noqa: ARG001
    context: Mapping[str, Any],
) -> Tuple[str, str]:
    payload = result.parsed_output
    if not isinstance(payload, Mapping):
        return "incorrect result", "Output must be a JSON object."

    if payload.get("status") != "ok":
        return "error", f"Action reported failure: {payload}"

    expected_path = context.get("expected_path")
    actual_path = payload.get("path")
    if actual_path != expected_path:
        return "incorrect result", "Returned path does not match expected location."

    target_path = Path(actual_path)
    if not target_path.exists():
        return "error", "Attachment file was not created."

    expected_bytes = context.get("expected_bytes", b"")
    if target_path.read_bytes() != expected_bytes:
        return "incorrect result", "Saved file contents differ from expected payload."

    return "passed", "Attachment downloaded into workspace successfully."


def get_test_case() -> ActionTestCase:
    return ActionTestCase(
        name="download message attachment",
        base_input={"url": ""},
        prepare=_prepare_download_message_attachment,
        validator=_validate_download_message_attachment,
    )
